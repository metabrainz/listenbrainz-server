import psycopg2
from psycopg2.extras import DictCursor

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user

from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.api_tools import get_non_negative_param


collection_bp = Blueprint("collection", __name__)

DEFAULT_COLLECTION_TRACKS_PER_CALL = 100
MAX_COLLECTION_TRACKS_PER_CALL = 500


def _fetch_collection_row(mb_curs, collection_mbid: str):
    mb_curs.execute(
        """
          SELECT ec.id AS collection_id
               , ec.gid::text AS collection_mbid
               , ec.name AS name
               , ec.public AS public
               , ec.editor AS owner_editor_id
            FROM musicbrainz.editor_collection ec
           WHERE ec.gid = %s
        """,
        (collection_mbid,),
    )
    return mb_curs.fetchone()


def _fetch_recording_collection_track_count(mb_curs, collection_id: int) -> int:
    mb_curs.execute(
        """
          SELECT COUNT(*)::int AS track_count
            FROM musicbrainz.editor_collection_recording ecr
           WHERE ecr.collection = %s
        """,
        (collection_id,),
    )
    row = mb_curs.fetchone()
    return int(row["track_count"] or 0)


def _fetch_recording_collection_tracks(mb_curs, collection_id: int, *, count: int, offset: int):
    mb_curs.execute(
        """
          SELECT r.gid::text AS recording_mbid
               , r.name AS title
               , r.length AS length
               , ac.name AS artist_credit_name
            FROM musicbrainz.editor_collection_recording ecr
            JOIN musicbrainz.recording r
              ON r.id = ecr.recording
            JOIN musicbrainz.artist_credit ac
              ON ac.id = r.artist_credit
           WHERE ecr.collection = %s
           ORDER BY ecr.position NULLS LAST, ecr.id
           LIMIT %s OFFSET %s
        """,
        (collection_id, count, offset),
    )
    return mb_curs.fetchall()


def fetch_collection_payload(collection_mbid: str, *, viewer_editor_id: int | None, count: int, offset: int):
    """Fetch collection and tracks from the MusicBrainz database.
    """
    if not is_valid_uuid(collection_mbid):
        return None, ({"error": f"Provided collection ID is invalid: {collection_mbid}"}, 400)

    if not current_app.config.get("MB_DATABASE_URI"):
        return None, ({"error": "MusicBrainz database is not configured on this server"}, 503)

    if count <= 0:
        return None, ({"error": "count must be a positive integer"}, 400)
    if count > MAX_COLLECTION_TRACKS_PER_CALL:
        return None, ({"error": f"count must be <= {MAX_COLLECTION_TRACKS_PER_CALL}"}, 400)
    if offset < 0:
        return None, ({"error": "offset must be a non-negative integer"}, 400)

    try:
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                mb_conn.cursor(cursor_factory=DictCursor) as mb_curs:
            collection = _fetch_collection_row(mb_curs, collection_mbid)
            if not collection:
                return None, ({"error": f"Collection {collection_mbid} not found in the MusicBrainz database"}, 404)

            if not collection["public"]:
                if viewer_editor_id is None:
                    return None, ({"error": "You must be logged in to access this collection"}, 401)
                if int(collection["owner_editor_id"]) != int(viewer_editor_id):
                    return None, ({"error": "You are not allowed to access this collection"}, 403)

            collection_id = int(collection["collection_id"])
            track_count = _fetch_recording_collection_track_count(mb_curs, collection_id)
            tracks = _fetch_recording_collection_tracks(
                mb_curs,
                collection_id,
                count=count,
                offset=offset,
            )
    except Exception:
        current_app.logger.error("Error fetching MusicBrainz collection:", exc_info=True)
        return None, ({"error": "Failed to fetch collection from MusicBrainz. Please try again."}, 500)

    payload = {
        "collection": {
            "mbid": collection["collection_mbid"],
            "name": collection["name"],
            "public": bool(collection["public"]),
        },
        "track_count": track_count,
        "count": count,
        "offset": offset,
        "tracks": [
            {
                "recording_mbid": t["recording_mbid"],
                "title": t["title"],
                "artist_credit_name": t["artist_credit_name"],
                "length": t["length"],
            }
            for t in tracks
        ],
    }
    return payload, None


@collection_bp.get("/", defaults={"collection_mbid": ""})
@collection_bp.get("/<collection_mbid>/")
def collection_page(collection_mbid: str):
    return render_template("index.html")


@collection_bp.post("/<collection_mbid>/")
@web_listenstore_needed
def load_collection(collection_mbid: str):
    viewer_editor_id = current_user.musicbrainz_row_id if current_user.is_authenticated else None
    count = get_non_negative_param("count", DEFAULT_COLLECTION_TRACKS_PER_CALL)
    offset = get_non_negative_param("offset", 0)
    payload, error = fetch_collection_payload(
        collection_mbid,
        viewer_editor_id=viewer_editor_id,
        count=count,
        offset=offset,
    )
    if error:
        body, code = error
        return jsonify(body), code
    return jsonify(payload)

