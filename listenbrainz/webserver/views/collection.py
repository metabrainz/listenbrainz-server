import psycopg2
from psycopg2.extras import DictCursor

from flask import Blueprint, current_app,render_template
from flask_login import current_user
from brainzutils.ratelimit import ratelimit

from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects
from listenbrainz.webserver import ts_conn
from listenbrainz.webserver.decorators import web_musicbrainz_needed
from listenbrainz.webserver.views.api_tools import is_valid_uuid
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
            JOIN musicbrainz.recording r
              ON r.id = ecr.recording
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
           ORDER BY ecr.position NULLS LAST, ecr.recording
           LIMIT %s OFFSET %s
        """,
        (collection_id, count, offset),
    )
    return mb_curs.fetchall()


def _serialize_collection_track(track_row, metadata_row=None) -> dict:
    """Build API track dict from MB collection row and optional metadata cache enrichment."""
    track = {
        "recording_mbid": track_row["recording_mbid"],
        "title": track_row["title"],
        "artist_credit_name": track_row["artist_credit_name"],
        "length": track_row["length"],
    }
    if not metadata_row or not metadata_row.get("recording_mbid"):
        return track

    if metadata_row.get("recording_name"):
        track["title"] = metadata_row["recording_name"]
    if metadata_row.get("artist_credit_name"):
        track["artist_credit_name"] = metadata_row["artist_credit_name"]
    if metadata_row.get("length") is not None:
        track["length"] = metadata_row["length"]
    if metadata_row.get("release_mbid"):
        track["release_mbid"] = metadata_row["release_mbid"]
    if metadata_row.get("release_name"):
        track["release_name"] = metadata_row["release_name"]
    if metadata_row.get("caa_id") is not None:
        track["caa_id"] = metadata_row["caa_id"]
    if metadata_row.get("caa_release_mbid"):
        track["caa_release_mbid"] = metadata_row["caa_release_mbid"]
    if metadata_row.get("artist_credit_mbids"):
        track["artist_mbids"] = metadata_row["artist_credit_mbids"]
    if metadata_row.get("artists"):
        track["artists"] = metadata_row["artists"]
    return track


def _enrich_recording_collection_tracks(mb_curs, tracks) -> list[dict]:
    """Enrich collection tracks using the same metadata cache path as playlists."""
    if not tracks:
        return []

    recording_mbids = [t["recording_mbid"] for t in tracks]
    metadata_by_mbid = {}
    try:
        with ts_conn.connection.cursor(cursor_factory=DictCursor) as ts_curs:
            metadata_rows = load_recordings_from_mbids_with_redirects(
                mb_curs, ts_curs, recording_mbids,
            )
        for row in metadata_rows:
            metadata_by_mbid[row["original_recording_mbid"]] = row
    except Exception:
        current_app.logger.error(
            "Error enriching MusicBrainz collection tracks from metadata cache:",
            exc_info=True,
        )

    return [
        _serialize_collection_track(t, metadata_by_mbid.get(t["recording_mbid"]))
        for t in tracks
    ]


def _get_cover_art_options_from_tracks(tracks: list[dict]) -> list[dict]:
    """Collect unique cover art images from enriched tracks"""
    selected_image_ids = set()
    images = []

    for track in tracks:
        caa_id = track.get("caa_id")
        caa_release_mbid = track.get("caa_release_mbid")
        if not (caa_id and caa_release_mbid):
            continue

        unique_key = f"{caa_id}-{caa_release_mbid}"
        if unique_key in selected_image_ids:
            continue
        selected_image_ids.add(unique_key)
        images.append({
            "caa_id": caa_id,
            "caa_release_mbid": caa_release_mbid,
            "title": track.get("title"),
            "entity_mbid": track.get("recording_mbid"),
            "artist": track.get("artist_credit_name"),
        })

    return images


def _generate_collection_cover_art(collection_name: str, tracks: list[dict]) -> str | None:
    """Build playlist-style mosaic SVG for the collection header from track cover art."""
    images = _get_cover_art_options_from_tracks(tracks)
    if not images:
        return None

    selected_cover_art = CoverArtGenerator.select_best_layout(len(images))
    cac = CoverArtGenerator(
        current_app.config["MB_DATABASE_URI"],
        selected_cover_art["dimension"],
        500,
        server_root_url=current_app.config["SERVER_ROOT_URL"],
    )
    if (validation_error := cac.validate_parameters()) is not None:
        current_app.logger.warning(
            "Invalid cover art parameters for collection %s: %s",
            collection_name,
            validation_error,
        )
        return None

    cover_art_images = cac.generate_from_caa_ids(
        images, layout=selected_cover_art["layout"], cover_art_size=500,
    )
    return render_template(
        "art/svg-templates/simple-grid.svg",
        background="transparent",
        images=cover_art_images,
        title=collection_name,
        desc="",
        entity="album",
        width=500,
        height=500,
        show_caption=False,
    )


def fetch_collection_payload(collection_mbid: str, *, viewer_editor_id: int | None, count: int, offset: int):
    """Fetch collection and tracks from the MusicBrainz database."""
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
            enriched_tracks = _enrich_recording_collection_tracks(mb_curs, tracks)
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
        "tracks": enriched_tracks,
    }

    if offset == 0:
        try:
            payload["cover_art"] = _generate_collection_cover_art(
                collection["name"], enriched_tracks,
            )
        except Exception:
            current_app.logger.error(
                "Error generating cover art for MusicBrainz collection:",
                exc_info=True,
            )
            payload["cover_art"] = None
    else:
        payload["cover_art"] = None

    return payload, None
 
@collection_bp.get("/", defaults={"collection_mbid": ""})
@collection_bp.get("/<collection_mbid>/")
@web_musicbrainz_needed
def collection_page(collection_mbid: str):
    return render_template("index.html")

