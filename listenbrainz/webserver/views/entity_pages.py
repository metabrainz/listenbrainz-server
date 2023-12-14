from datetime import datetime

from flask import Blueprint, render_template, current_app

from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.db import timescale
from listenbrainz.db.metadata import get_metadata_for_artist
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.db.popularity import get_top_entity_for_entity
from listenbrainz.webserver.views.metadata_api import fetch_release_group_metadata
import requests
from werkzeug.exceptions import BadRequest, NotFound
import orjson
import psycopg2
import psycopg2.extras

artist_bp = Blueprint("artist", __name__)
album_bp = Blueprint("album", __name__)
release_bp = Blueprint("release", __name__)

# Problems / TODO / Goals
# - These view functions need to be cleaned up so that for each artist / release group page,
#   we only make two DB accesses: the cached MB data and the populartity data. This far from the
#   case right now, since we build the caches with what we thought we inittially needed. However,
#   all the things that are tacked onto this module are all the things we forgot about, so now those
#   need to get moved to a proper home in the cached data.
# - Need to find the canonical release
# - Need to have popularity data
# - MB data doesnt change very often. Popularity data, constantly

# Test cases
# with cover art: 48140466-cff6-3222-bd55-63c27e43190d
# without : 061e2733-aa87-3ca6-bbec-3303ca1a2760


def get_release_group_sort_key(release_group):
    """ Return a tuple that sorts release group by total_listen_count and then by date """
    release_date = release_group.get("date")
    if release_date is None:
        release_date = datetime.min
    else:
        release_date = datetime.strptime(release_date, "%Y-%m-%d")

    return release_group["total_listen_count"] or 0, release_date


def get_cover_art_for_artist(release_groups):
    """ Get the cover art for an artist using a list of their release groups """
    covers = [rg for rg in release_groups if rg.get("caa_id") is not None]
    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"],
        4,
        400,
        "transparent",
        True,
        False
    )
    images = cac.generate_from_caa_ids(covers, [
        "0,1,4,5",
        "10,11,14,15",
        "2",
        "3",
        "6",
        "7",
        "8",
        "9",
        "12",
        "13",
      ], None, 250)
    return render_template(
        "art/svg-templates/simple-grid.svg",
        background="transparent",
        images=images,
        width=400,
        height=400
    )


@release_bp.route("/<release_group_mbid>", methods=["GET"])
@web_listenstore_needed
def release_redirect(release_group_mbid):
    # TODO: Load release_group and redirect to it
    pass


@artist_bp.route("/<artist_mbid>", methods=["GET"])
@web_listenstore_needed
def artist_entity(artist_mbid):
    """ Show a artist page with all their relevant information """

    if not is_valid_uuid(artist_mbid):
        raise BadRequest("Provided artist ID is invalid: %s" % artist_mbid)

    # Fetch the artist cached data
    artist_data = get_metadata_for_artist([artist_mbid])
    if len(artist_data) == 0:
        raise NotFound(f"artist {artist_mbid} not found in the metadata cache")

    artist = {
        "artist_mbid": str(artist_data[0].artist_mbid),
        **artist_data[0].artist_data,
        "tag": artist_data[0].tag_data,
    }

    # Fetch top recordings for artist
    params = {"artist_mbid": artist_mbid, 'count': 10}
    r = requests.get(url="https://api.listenbrainz.org/1/popularity/top-recordings-for-artist", params=params)
    if r.status_code != 200:
        popular_recordings = []
    else:
        popular_recordings = list(r.json())[:10]

    popular_recordings = popularity.get_top_recordings_for_artist(artist_mbid, 10)

    try:
        artists = r.json()[3]["data"][:15]
    except IndexError:
        artists = []

    release_group_data = artist_data[0].release_group_data
    release_group_mbids = [rg["mbid"] for rg in release_group_data]
    popularity_data = popularity.get_counts("release_group", release_group_mbids)

    # General note: This whole view function is a disaster, yes. But it is only so that monkey can work on the
    # UI for these pages. The next project will be to collect all this data and store it in couchdb.
    top_release_groups = get_top_entity_for_entity("release-group", artist_mbid, "release-group")
    release_group_mbids = tuple([str(k["release_group_mbid"]) for k in top_release_groups])

    try:
        cover_art = get_cover_art_for_artist(release_groups)
    except Exception:
        current_app.logger.error("Error generating cover art for artist:", exc_info=True)
        cover_art = None

    props = {
        "artist_data": item,
        "popular_recordings": popular_recordings,
        "similar_artists": artists,
        "listening_stats": {},
        # TODO: These stats need to be moved into its own cached data set.
        # total plays for artist
        # total # of listeners for artist
        # top listeners (10)
        "release_groups": release_groups,
        "cover_art": cover_art
    }

    return render_template("entities/artist.html",
                           props=orjson.dumps(props).decode("utf-8"),
                           title=artist_data[0].artist_data["name"])


@album_bp.route("/<release_group_mbid>", methods=["GET"])
@web_listenstore_needed
def album_entity(release_group_mbid):
    """ Show an album page with all their relevant information """

    if not is_valid_uuid(release_group_mbid):
        raise BadRequest("Provided release group ID is invalid: %s" % release_group_mbid)

    # Fetch the release group cached data
    metadata = fetch_release_group_metadata(
        [release_group_mbid],
        ["artist", "tag", "release", "recording"]
    )
    if len(metadata) == 0:
        raise NotFound(f"Release group {release_group_mbid} not found in the metadata cache")
    release_group = metadata[release_group_mbid]

    pop_query = """SELECT recording_mbid::TEXT
                        , total_listen_count
                        , total_user_count
                     FROM popularity.recording
                    WHERE recording_mbid in %s"""

    recording_data = release_group.pop("recording").get("recordings", [])
    recording_mbids = [rec["recording_mbid"] for rec in recording_data]
    with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as lb_conn:
        with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            lb_curs.execute(pop_query, (tuple(recording_mbids), ))
            popularity = [dict(row) for row in lb_curs.fetchall()]

    pop_index = {row["recording_mbid"]: (row["total_listen_count"], row["total_user_count"]) for row in popularity}

    recordings = []
    for rec in recording_data:
        recording = dict(rec)
        try:
            recording["total_listen_count"] = pop_index[rec[2]][0]
            recording["total_user_count"] = pop_index[rec[2]][1]
        except KeyError:
            recording["total_listen_count"] = None
            recording["total_user_count"] = None
        recordings.append(recording)

    props = {
        "release_group_mbid": release_group_mbid,
        "release_group_metadata": release_group,
        "recordings": recordings,
        "caa_id": release_group["release_group"]["caa_id"],
        "caa_release_mbid": release_group["release_group"]["caa_release_mbid"],
        "type": release_group["release_group"].get("type")
    }

    return render_template("entities/album.html",
                           props=orjson.dumps(props).decode("utf-8"),
                           title=release_group["release_group"]["name"])
