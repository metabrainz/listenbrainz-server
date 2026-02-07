from datetime import datetime

from flask import Blueprint, render_template, current_app, jsonify
from werkzeug.exceptions import BadRequest

from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.db import popularity, similarity
from listenbrainz.db.stats import get_entity_listener
from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects, load_release_groups_for_recordings
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.utils import number_readable
from listenbrainz.db.metadata import get_metadata_for_artist
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.metadata_api import fetch_release_group_metadata, fetch_metadata
import psycopg2
from psycopg2.extras import DictCursor
from listenbrainz.db.genre import find_tagged_entities, load_genres_from_mbids

artist_bp = Blueprint("artist", __name__)
album_bp = Blueprint("album", __name__)
release_bp = Blueprint("release", __name__)
release_group_bp = Blueprint("release-group", __name__)
track_bp = Blueprint("track", __name__)
recording_bp = Blueprint("recording", __name__)
genre_bp = Blueprint("genre", __name__)


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

    # Select the best layout based on available cover art
    selected_layout = CoverArtGenerator.select_best_layout(len(covers))
    if selected_layout is None:
        return None

    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"],
        selected_layout["dimension"],
        400,
        "transparent",
        True,
        False,
        server_root_url=current_app.config["SERVER_ROOT_URL"]
    )
    images = cac.generate_from_caa_ids(
        covers,
        layout=selected_layout["layout"],
        cover_art_size=250
    )
    return render_template(
        "art/svg-templates/simple-grid.svg",
        background="transparent",
        images=images,
        entity="album",
        width=400,
        height=400,
        show_caption=False
    )


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


@release_group_bp.get('/<path:path>/')
def release_group_redirect(path):
    return render_template("index.html")


@recording_bp.get('/<path:path>/')
def recording_redirect(path):
    return render_template("index.html")


@track_bp.get('/<recording_mbid>/')
def recording_page(recording_mbid: str):
    og_meta_tags = None
    if is_valid_uuid(recording_mbid):
        metadata = fetch_metadata(
            [recording_mbid],
            ["artist", "release"]
        )
        if len(metadata) == 0:
            pass
        else:
            recording = metadata[recording_mbid]
            recording_name = recording.get("recording").get("name")
            artist_name = recording.get("artist").get("name")
            release_group_mbid = recording.get("release").get("release_group_mbid")

            og_meta_tags = {
                "title": f'{recording_name} — {artist_name}',
                "description": f'Recording — ListenBrainz',
                "type": "music.song",
                "music:musician": artist_name,
                "music:release_date": recording.get("release").get("date"),
                "image": f'https://coverartarchive.org/release-group/{release_group_mbid}/front-500',
                "image:width": "500",
                "image:alt": f"Cover art for {recording_name}",
                "url": f'{current_app.config["SERVER_ROOT_URL"]}/track/{recording_mbid}',
            }

    return render_template("index.html", og_meta_tags=og_meta_tags)


@track_bp.post("/<recording_mbid>/")
@web_listenstore_needed
def recording_entity(recording_mbid: str):
    """ Show a recording page with all their relevant information """

    if not is_valid_uuid(recording_mbid):
        return jsonify({"error": "Provided recording mbid is invalid: %s" % recording_mbid}), 400

    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
            psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
            mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
            ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:
        recording_data = load_recordings_from_mbids_with_redirects(mb_curs, ts_curs, [recording_mbid])
    if recording_data is None or len(recording_data) == 0 or recording_data[0].get("recording_mbid") is None:
        return jsonify({"error": f"Recording {recording_mbid} not found in the metadata cache"}), 404

    recording_data = recording_data[0]

    try:
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                mb_conn.cursor(cursor_factory=DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:

            similar_recordings = similarity.get_recordings(
                mb_curs,
                ts_curs,
                [recording_mbid],
                "session_based_days_7500_session_300_contribution_5_threshold_15_limit_50_skip_30_top_n_listeners_1000",
                18
            )
            similar_recording_mbids = [recording["recording_mbid"] for recording in similar_recordings]
            similar_recordings_data = load_recordings_from_mbids_with_redirects(mb_curs, ts_curs, similar_recording_mbids)
    except Exception:
        current_app.logger.error("Error loading similar recordings:", exc_info=True)
        similar_recordings_data = []

    try:
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                mb_conn.cursor(cursor_factory=DictCursor) as mb_curs:
            release_groups_data = load_release_groups_for_recordings(mb_curs, [recording_mbid])
            release_groups_data = list(release_groups_data.values())
    except Exception:
        current_app.logger.error("Error loading release groups for recording:", exc_info=True)
        release_groups_data = []

    release_group_mbids = [rg["mbid"] for rg in release_groups_data]
    try:
        with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                ts_conn.cursor(cursor_factory=DictCursor) as ts_curs:
            popularity_data, _ = popularity.get_counts(ts_curs, "release_group", release_group_mbids)
    except Exception:
        current_app.logger.error("Error loading popularity data for release groups:", exc_info=True)
        popularity_data = []

    release_groups = []
    for release_group, pop in zip(release_groups_data, popularity_data):
        release_group["total_listen_count"] = pop["total_listen_count"]
        release_group["total_user_count"] = pop["total_user_count"]
        release_groups.append(release_group)

    data = {
        "track_mbid": recording_mbid,
        "track": recording_data,
        "similarTracks": similar_recordings_data,
        "releaseGroups": release_groups,
    }

    return jsonify(data)


@genre_bp.get('/<genre_mbid>/')
def genre_page(genre_mbid: str):
    return render_template("index.html")


@genre_bp.post("/<genre_mbid>/")
@web_listenstore_needed
def genre_entity(genre_mbid: str):
    """ Show a genre page with all their relevant information """

    if not is_valid_uuid(genre_mbid):
        return jsonify({"error": "Provided genre mbid is invalid: %s" % genre_mbid}), 400

    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
            mb_conn.cursor(cursor_factory=DictCursor) as mb_curs:
        genre_data = load_genres_from_mbids(mb_curs, [genre_mbid])

        if genre_data is None or len(genre_data) == 0 or genre_mbid not in genre_data:
            return jsonify({"error": f"Genre {genre_mbid} not found in the metadata cache"}), 404

        genre = genre_data[genre_mbid]
        genre_dict = dict(genre)
        genre_name = genre_dict.get("name") or ""
        tagged_entities = find_tagged_entities(mb_curs, genre_name)

    # Enrich release_group entities with full metadata and listen counts (only RGs in our cache)
    rg_entities = tagged_entities.get("release_group", {}).get("entities", [])
    if rg_entities:
        release_group_mbids = [e["mbid"] for e in rg_entities]
        rg_metadata = fetch_release_group_metadata(release_group_mbids, ["artist"])
        popularity_data, _ = popularity.get_counts(
            ts_conn, "release_group", release_group_mbids
        )
        pop_by_mbid = {pop["release_group_mbid"]: pop for pop in popularity_data}
        enriched_rg = []
        for entity in rg_entities:
            mbid = entity["mbid"]
            meta = rg_metadata.get(mbid)
            if not meta:
                continue
            pop = pop_by_mbid.get(mbid, {})
            rg = meta["release_group"]
            artist = meta.get("artist") or {}
            enriched_rg.append({
                "mbid": mbid,
                "name": rg.get("name"),
                "date": rg.get("date"),
                "type": rg.get("type"),
                "caa_id": rg.get("caa_id"),
                "caa_release_mbid": rg.get("caa_release_mbid"),
                "artist_credit_name": artist.get("name"),
                "artists": artist.get("artists", []),
                "tag_count": entity.get("tag_count"),
                "total_listen_count": pop.get("total_listen_count"),
                "total_user_count": pop.get("total_user_count"),
            })
        tagged_entities["release_group"]["entities"] = enriched_rg

    return jsonify({
        "genre": genre_dict,
        "genre_mbid": genre_mbid,
        "entities": tagged_entities,
    })
