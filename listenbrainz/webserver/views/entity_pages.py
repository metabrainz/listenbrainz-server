from datetime import datetime

from flask import Blueprint, render_template, current_app, redirect, url_for

from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.db import popularity, similarity
from listenbrainz.db.stats import get_entity_listener
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.db.metadata import get_metadata_for_artist
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.metadata_api import fetch_release_group_metadata
from werkzeug.exceptions import BadRequest, NotFound
import orjson
import psycopg2
from psycopg2.extras import DictCursor

artist_bp = Blueprint("artist", __name__)
album_bp = Blueprint("album", __name__)
release_bp = Blueprint("release", __name__)
release_group_bp = Blueprint("release-group", __name__)


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
    covers = []
    for release_group in release_groups:
        if release_group.get("caa_id") is not None:
            cover = {
                "entity_mbid": release_group["mbid"],
                "title": release_group["name"],
                "artist": release_group["artist_credit_name"],
                "caa_id": release_group["caa_id"],
                "caa_release_mbid": release_group["caa_release_mbid"]
            }
            covers.append(cover)

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
        entity="album",
        width=400,
        height=400
    )


@release_bp.route("/<release_mbid>/", methods=["GET"])
@web_listenstore_needed
def release_redirect(release_mbid):
    if not is_valid_uuid(release_mbid):
        raise BadRequest("Provided release mbid is invalid: %s" % release_mbid)

    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn,\
            mb_conn.cursor(cursor_factory=DictCursor) as mb_curs:
        mb_curs.execute("""
            SELECT rg.gid AS release_group_mbid
              FROM musicbrainz.release rel
              JOIN musicbrainz.release_group rg
                ON rel.release_group = rg.id
             WHERE rel.gid = %s
        """, (release_mbid,))
        result = mb_curs.fetchone()
        if result is None:
            raise NotFound(f"Release {release_mbid} not found in the metadata cache")
        return redirect(url_for("album.album_entity", release_group_mbid=result["release_group_mbid"]))


@artist_bp.route("/<artist_mbid>/", methods=["GET"])
@web_listenstore_needed
def artist_entity(artist_mbid):
    """ Show a artist page with all their relevant information """

    if not is_valid_uuid(artist_mbid):
        raise BadRequest("Provided artist mbid is invalid: %s" % artist_mbid)

    # Fetch the artist cached data
    artist_data = get_metadata_for_artist([artist_mbid])
    if len(artist_data) == 0:
        raise NotFound(f"artist {artist_mbid} not found in the metadata cache")

    artist = {
        "artist_mbid": str(artist_data[0].artist_mbid),
        **artist_data[0].artist_data,
        "tag": artist_data[0].tag_data,
    }

    popular_recordings = popularity.get_top_recordings_for_artist(artist_mbid, 10)

    try:
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=DictCursor) as ts_curs:

            similar_artists = similarity.get_artists(
                mb_curs,
                ts_curs,
                [artist_mbid],
                "session_based_days_7500_session_300_contribution_3_threshold_10_limit_100_filter_True_skip_30",
                15
            )
    except IndexError:
        similar_artists = []

    release_group_data = artist_data[0].release_group_data
    release_group_mbids = [rg["mbid"] for rg in release_group_data]
    popularity_data = popularity.get_counts("release_group", release_group_mbids)

    release_groups = []
    for release_group, pop in zip(release_group_data, popularity_data):
        release_group["total_listen_count"] = pop["total_listen_count"]
        release_group["total_user_count"] = pop["total_user_count"]
        release_groups.append(release_group)

    release_groups.sort(key=get_release_group_sort_key, reverse=True)

    listening_stats = get_entity_listener("artists", artist_mbid, "all_time")
    if listening_stats is None:
        listening_stats = {
            "total_listen_count": 0,
            "listeners": []
        }

    try:
        cover_art = get_cover_art_for_artist(release_groups)
    except Exception:
        current_app.logger.error("Error generating cover art for artist:", exc_info=True)
        cover_art = None

    props = {
        "artist_data": artist,
        "popular_recordings": popular_recordings,
        "similar_artists": similar_artists,
        "listening_stats": listening_stats,
        "release_groups": release_groups,
        "cover_art": cover_art
    }

    return render_template("entities/artist.html",
                           props=orjson.dumps(props).decode("utf-8"),
                           title=artist_data[0].artist_data["name"])


@album_bp.route("/<release_group_mbid>/", methods=["GET"])
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
        raise NotFound(f"Release group mbid {release_group_mbid} not found in the metadata cache")
    release_group = metadata[release_group_mbid]

    recording_data = release_group.pop("recording").get("recordings", [])
    recording_mbids = [rec["recording_mbid"] for rec in recording_data]
    popularity_data = popularity.get_counts("recording", recording_mbids)

    recordings = []
    for rec, pop in zip(recording_data, popularity_data):
        recording = dict(rec)
        recording["total_listen_count"] = pop["total_listen_count"]
        recording["total_user_count"] = pop["total_user_count"]
        recordings.append(recording)

    listening_stats = get_entity_listener("release_groups", release_group_mbid, "all_time")
    if listening_stats is None:
        listening_stats = {
            "total_listen_count": 0,
            "listeners": []
        }

    props = {
        "release_group_mbid": release_group_mbid,
        "release_group_metadata": release_group,
        "recordings": recordings,
        "caa_id": release_group["release_group"]["caa_id"],
        "caa_release_mbid": release_group["release_group"]["caa_release_mbid"],
        "type": release_group["release_group"].get("type"),
        "listening_stats": listening_stats
    }

    return render_template("entities/album.html",
                           props=orjson.dumps(props).decode("utf-8"),
                           title=release_group["release_group"]["name"])


@release_group_bp.route("/<release_group_mbid>/", methods=["GET"])
def release_group_redirect(release_group_mbid):
    """ Redirect to the /album/… page. Intended for better interplay with MusicBrainz URLs """
    return redirect(url_for("album.album_entity", release_group_mbid=release_group_mbid))
