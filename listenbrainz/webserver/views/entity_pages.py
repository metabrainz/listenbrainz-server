from datetime import datetime

from flask import Blueprint, render_template, current_app, jsonify
from werkzeug.exceptions import BadRequest

from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.db import popularity, similarity
from listenbrainz.db.stats import get_entity_listener
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.utils import number_readable
from listenbrainz.db.metadata import get_metadata_for_artist
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.metadata_api import fetch_release_group_metadata
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
        # Add default month/day if missing
        parts = release_date.split('-')
        if len(parts) == 1:  # YYYY
            release_date += "-01-01"
        elif len(parts) == 2:  # YYYY-MM
            release_date += "-01"

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


@release_bp.get("/",  defaults={'path': ''})
@release_bp.get('/<path:path>/')
def release_page(path):
    return render_template("index.html")


@release_bp.post("/<release_mbid>/")
@web_listenstore_needed
def release_redirect(release_mbid):
    if not is_valid_uuid(release_mbid):
        return jsonify({"error": "Provided release mbid is invalid: %s" % release_mbid}), 400

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
            return jsonify({"error": f"Release {release_mbid} not found in the MusicBrainz database"}), 404

        return jsonify({"releaseGroupMBID": result["release_group_mbid"]})


@artist_bp.get("/",  defaults={'path': ''})
@artist_bp.get("/<artist_mbid>/")
def artist_page(artist_mbid: str):
    og_meta_tags = None
    if is_valid_uuid(artist_mbid) and artist_mbid not in {"89ad4ac3-39f7-470e-963a-56509c546377"}:
        artist_data = get_metadata_for_artist(ts_conn, [artist_mbid])
        if len(artist_data) == 0:
            pass
        else:
            artist = artist_data[0]
            artist_name = artist.artist_data.get("name")
            release_group_data = artist.release_group_data
            release_group_mbids = [rg["mbid"] for rg in release_group_data]
            album_count = len(release_group_mbids)
            listening_stats = get_entity_listener(
                db_conn, "artists", artist_mbid, "all_time")
            total_listen_count = 0
            if listening_stats and "total_listen_count" in listening_stats:
                total_listen_count = number_readable(
                    listening_stats["total_listen_count"] or 0)

            og_meta_tags = {
                "title": f'{artist_name}',
                "description": f'Artist — {total_listen_count} listens — {album_count} albums — ListenBrainz',
                "type": "profile",
                "profile:username": artist_name,
                "profile.gender": artist.artist_data.get("gender"),
                "url": f'{current_app.config["SERVER_ROOT_URL"]}/artist/{artist.artist_mbid}',
            }
    return render_template("index.html", og_meta_tags=og_meta_tags)


@artist_bp.post("/<artist_mbid>/")
@web_listenstore_needed
def artist_entity(artist_mbid: str):
    """ Show a artist page with all their relevant information """
    # VA artist mbid
    if artist_mbid in {"89ad4ac3-39f7-470e-963a-56509c546377"}:
        return jsonify({"error": "Provided artist mbid is disabled for viewing on ListenBrainz"}), 400

    if not is_valid_uuid(artist_mbid):
        return jsonify({"error": "Provided artist mbid is invalid: %s" % artist_mbid}), 400

    # Fetch the artist cached data
    artist_data = get_metadata_for_artist(ts_conn, [artist_mbid])
    if len(artist_data) == 0:
        return jsonify({"error": f"artist {artist_mbid} not found in the metadata cache"}), 404

    artist = {
        "artist_mbid": str(artist_data[0].artist_mbid),
        **artist_data[0].artist_data,
        "tag": artist_data[0].tag_data,
    }

    popular_recordings = popularity.get_top_recordings_for_artist(db_conn, ts_conn, artist_mbid, 10)

    try:
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                mb_conn.cursor(cursor_factory=DictCursor) as mb_curs, \
                ts_conn.connection.cursor(cursor_factory=DictCursor) as ts_curs:

            similar_artists = similarity.get_artists(
                mb_curs,
                ts_curs,
                [artist_mbid],
                "session_based_days_7500_session_300_contribution_3_threshold_10_limit_100_filter_True_skip_30",
                18
            )
    except IndexError:
        similar_artists = []

    try:
        top_release_group_color = popularity.get_top_release_groups_for_artist(
            db_conn, ts_conn, artist_mbid, 1
        )[0]["release_color"]
    except IndexError:
        top_release_group_color = None

    try:
        top_recording_color = popularity.get_top_recordings_for_artist(db_conn, ts_conn, artist_mbid, 1)[0]["release_color"]
    except IndexError:
        top_recording_color = None

    release_group_data = artist_data[0].release_group_data
    release_group_mbids = [rg["mbid"] for rg in release_group_data]
    popularity_data, _ = popularity.get_counts(ts_conn, "release_group", release_group_mbids)

    release_groups = []
    for release_group, pop in zip(release_group_data, popularity_data):
        release_group["total_listen_count"] = pop["total_listen_count"]
        release_group["total_user_count"] = pop["total_user_count"]
        release_groups.append(release_group)

    release_groups.sort(key=get_release_group_sort_key, reverse=True)

    listening_stats = get_entity_listener(db_conn, "artists", artist_mbid, "all_time")
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

    data = {
        "artist": artist,
        "popularRecordings": popular_recordings,
        "similarArtists": {
            "artists": similar_artists,
            "topReleaseGroupColor": top_release_group_color,
            "topRecordingColor": top_recording_color
        },
        "listeningStats": listening_stats,
        "releaseGroups": release_groups,
        "coverArt": cover_art
    }

    return jsonify(data)


@album_bp.get("/",  defaults={'path': ''})
@album_bp.get("/<release_group_mbid>/")
def album_page(release_group_mbid: str):
    og_meta_tags = None
    if is_valid_uuid(release_group_mbid):
        metadata = fetch_release_group_metadata(
            [release_group_mbid],
            ["artist", "recording"]
        )
        if len(metadata) == 0:
            pass
        else:
            release_group = metadata[release_group_mbid]

            recording_data = release_group.pop("recording")
            mediums = recording_data.get("mediums", [])
            recording_mbids = []
            for medium in mediums:
                for track in medium["tracks"]:
                    recording_mbids.append(track["recording_mbid"])

            album_name = release_group.get("release_group").get("name")
            artist_name = release_group.get("artist").get("name")
            track_count = len(recording_mbids)
            listening_stats = get_entity_listener(
                db_conn, "release_groups", release_group_mbid, "all_time")
            total_listen_count = 0
            if listening_stats and "total_listen_count" in listening_stats:
                total_listen_count = number_readable(
                    listening_stats["total_listen_count"] or 0)

            og_meta_tags = {
                "title": f'{album_name} — {artist_name}',
                "description": f'Album — {track_count} tracks — {total_listen_count} listens — ListenBrainz',
                "type": "music.album",
                "music:musician": artist_name,
                "music:release_date": release_group.get("release_group").get("date"),
                "image": f'https://coverartarchive.org/release-group/{release_group_mbid}/front-500',
                "image:width": "500",
                "image:alt": f"Cover art for {album_name}",
                "url": f'{current_app.config["SERVER_ROOT_URL"]}/album/{release_group_mbid}',
            }

    return render_template("index.html", og_meta_tags=og_meta_tags)


@album_bp.post("/<release_group_mbid>/")
@web_listenstore_needed
def album_entity(release_group_mbid: str):
    """ Show an album page with all their relevant information """

    if not is_valid_uuid(release_group_mbid):
        return jsonify({"error": "Provided release group ID is invalid: %s" % release_group_mbid}), 400

    # Fetch the release group cached data
    metadata = fetch_release_group_metadata(
        [release_group_mbid],
        ["artist", "tag", "release", "recording"]
    )
    if len(metadata) == 0:
        return jsonify({"error": f"Release group mbid {release_group_mbid} not found in the metadata cache"}), 404
    release_group = metadata[release_group_mbid]

    recording_data = release_group.pop("recording")
    mediums = recording_data.get("mediums", [])
    recording_mbids = []
    for medium in mediums:
        for track in medium["tracks"]:
            recording_mbids.append(track["recording_mbid"])
    popularity_data, popularity_index = popularity.get_counts(ts_conn, "recording", recording_mbids)

    for medium in mediums:
        for track in medium["tracks"]:
            track["total_listen_count"], track["total_user_count"] = popularity_index.get(
                track["recording_mbid"],
                (None, None)
            )

    listening_stats = get_entity_listener(db_conn, "release_groups", release_group_mbid, "all_time")
    if listening_stats is None:
        listening_stats = {
            "total_listen_count": 0,
            "listeners": []
        }

    data = {
        "release_group_mbid": release_group_mbid,
        "release_group_metadata": release_group,
        "recordings_release_mbid": recording_data.get("release_mbid"),
        "mediums": mediums,
        "caa_id": release_group["release_group"]["caa_id"],
        "caa_release_mbid": release_group["release_group"]["caa_release_mbid"],
        "type": release_group["release_group"].get("type"),
        "listening_stats": listening_stats
    }

    return jsonify(data)


@release_group_bp.get("/",  defaults={'path': ''})
@release_group_bp.get('/<path:path>/')
def release_group_redirect(path):
    return render_template("index.html")
