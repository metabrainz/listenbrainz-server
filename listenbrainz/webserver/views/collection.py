import psycopg2
from psycopg2.extras import DictCursor

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user

from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.db.cover_art import get_caa_ids_for_release_mbids
from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects
from listenbrainz.webserver import ts_conn
from listenbrainz.webserver.decorators import web_musicbrainz_needed
from listenbrainz.webserver.views.api_tools import (
    get_non_negative_param,
    get_positive_param,
    is_valid_uuid,
)

collection_bp = Blueprint("collection", __name__)

DEFAULT_COLLECTION_TRACKS_PER_CALL = 100
MAX_COLLECTION_TRACKS_PER_CALL = 500
SUPPORTED_COLLECTION_ENTITY_TYPES = frozenset({"recording", "release"})


def _fetch_collection_row(mb_curs, collection_mbid: str):
    mb_curs.execute(
        """
          SELECT ec.id AS collection_id
               , ec.gid::text AS collection_mbid
               , ec.name AS name
               , ec.public AS public
               , ec.editor AS owner_editor_id
               , ect.entity_type AS entity_type
            FROM musicbrainz.editor_collection ec
            JOIN musicbrainz.editor_collection_type ect
              ON ect.id = ec.type
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


def _fetch_release_collection_item_count(mb_curs, collection_id: int) -> int:
    mb_curs.execute(
        """
          SELECT COUNT(*)::int AS item_count
            FROM musicbrainz.editor_collection_release ecrel
            JOIN musicbrainz.release rel
              ON rel.id = ecrel.release
           WHERE ecrel.collection = %s
        """,
        (collection_id,),
    )
    row = mb_curs.fetchone()
    return int(row["item_count"] or 0)


def _fetch_release_collection_flattened_track_count(mb_curs, collection_id: int) -> int:
    mb_curs.execute(
        """
          SELECT COUNT(*)::int AS track_count
            FROM musicbrainz.editor_collection_release ecrel
            JOIN musicbrainz.release rel
              ON rel.id = ecrel.release
            JOIN musicbrainz.medium m
              ON m.release = rel.id
            JOIN musicbrainz.track t
              ON t.medium = m.id
            JOIN musicbrainz.recording r
              ON r.id = t.recording
           WHERE ecrel.collection = %s
        """,
        (collection_id,),
    )
    row = mb_curs.fetchone()
    return int(row["track_count"] or 0)


def _fetch_release_collection_flattened_tracks(mb_curs, collection_id: int, *, count: int, offset: int):
    mb_curs.execute(
        """
          SELECT r.gid::text AS recording_mbid
               , r.name AS title
               , r.length AS length
               , ac.name AS artist_credit_name
               , rel.gid::text AS release_mbid
               , rel.name AS release_name
            FROM musicbrainz.editor_collection_release ecrel
            JOIN musicbrainz.release rel
              ON rel.id = ecrel.release
            JOIN musicbrainz.medium m
              ON m.release = rel.id
            JOIN musicbrainz.track t
              ON t.medium = m.id
            JOIN musicbrainz.recording r
              ON r.id = t.recording
            JOIN musicbrainz.artist_credit ac
              ON ac.id = r.artist_credit
           WHERE ecrel.collection = %s
           ORDER BY ecrel.position NULLS LAST
                  , rel.id
                  , m.position
                  , t.position
           LIMIT %s OFFSET %s
        """,
        (collection_id, count, offset),
    )
    return mb_curs.fetchall()


def _fetch_release_collection_items(mb_curs, collection_id: int, *, count: int, offset: int):
    mb_curs.execute(
        """
          SELECT rel.gid::text AS release_mbid
               , rel.name AS title
               , ac.name AS artist_credit_name
            FROM musicbrainz.editor_collection_release ecrel
            JOIN musicbrainz.release rel
              ON rel.id = ecrel.release
            JOIN musicbrainz.artist_credit ac
              ON ac.id = rel.artist_credit
           WHERE ecrel.collection = %s
           ORDER BY ecrel.position NULLS LAST, rel.id
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


def _get_cover_art_options_from_items(items: list[dict], *, entity_mbid_key: str) -> list[dict]:
    """Collect unique cover art images from enriched collection items/tracks."""
    selected_image_ids = set()
    images = []

    for item in items:
        caa_id = item.get("caa_id")
        caa_release_mbid = item.get("caa_release_mbid")
        if not (caa_id and caa_release_mbid):
            continue

        unique_key = f"{caa_id}-{caa_release_mbid}"
        if unique_key in selected_image_ids:
            continue
        selected_image_ids.add(unique_key)
        images.append({
            "caa_id": caa_id,
            "caa_release_mbid": caa_release_mbid,
            "title": item.get("title"),
            "entity_mbid": item.get(entity_mbid_key),
            "artist": item.get("artist_credit_name"),
        })

    return images


def _generate_collection_cover_art(
    collection_name: str,
    items: list[dict],
    *,
    entity_mbid_key: str = "recording_mbid",
) -> str | None:
    """Build playlist-style mosaic SVG for the collection header from cover art."""
    images = _get_cover_art_options_from_items(items, entity_mbid_key=entity_mbid_key)
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


def _serialize_recording_collection_payload(collection, collection_id: int, *, count: int, offset: int, mb_curs):
    track_count = _fetch_recording_collection_track_count(mb_curs, collection_id)
    tracks = _fetch_recording_collection_tracks(
        mb_curs,
        collection_id,
        count=count,
        offset=offset,
    )
    enriched_tracks = _enrich_recording_collection_tracks(mb_curs, tracks)
    payload = {
        "collection": {
            "mbid": collection["collection_mbid"],
            "name": collection["name"],
            "public": bool(collection["public"]),
            "entity_type": collection["entity_type"],
        },
        "track_count": track_count,
        "count": count,
        "offset": offset,
        "tracks": enriched_tracks,
        "items": [],
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

    return payload


def _serialize_release_item(release_row, cover_row=None) -> dict:
    """Build API release dict from MB collection row and optional CAA enrichment."""
    item = {
        "release_mbid": release_row["release_mbid"],
        "title": release_row["title"],
        "artist_credit_name": release_row["artist_credit_name"],
    }
    if cover_row and cover_row.get("caa_id") is not None and cover_row.get("caa_release_mbid"):
        item["caa_id"] = cover_row["caa_id"]
        item["caa_release_mbid"] = cover_row["caa_release_mbid"]
    return item


def _enrich_release_collection_items(mb_curs, releases) -> list[dict]:
    """Attach CAA ids to release collection items for thumbnails and header mosaic."""
    if not releases:
        return []

    release_mbids = [r["release_mbid"] for r in releases]
    covers_by_mbid = {}
    try:
        covers_by_mbid = get_caa_ids_for_release_mbids(mb_curs, release_mbids)
    except Exception:
        current_app.logger.error(
            "Error enriching MusicBrainz release collection items with cover art:",
            exc_info=True,
        )

    return [
        _serialize_release_item(r, covers_by_mbid.get(r["release_mbid"]))
        for r in releases
    ]


def _serialize_release_collection_payload(collection, collection_id: int, *, count: int, offset: int, mb_curs):
    item_count = _fetch_release_collection_item_count(mb_curs, collection_id)
    releases = _fetch_release_collection_items(
        mb_curs,
        collection_id,
        count=count,
        offset=offset,
    )
    enriched_items = _enrich_release_collection_items(mb_curs, releases)
    payload = {
        "collection": {
            "mbid": collection["collection_mbid"],
            "name": collection["name"],
            "public": bool(collection["public"]),
            "entity_type": collection["entity_type"],
        },
        "track_count": item_count,
        "count": count,
        "offset": offset,
        "tracks": [],
        "items": enriched_items,
    }

    if offset == 0:
        try:
            payload["cover_art"] = _generate_collection_cover_art(
                collection["name"],
                enriched_items,
                entity_mbid_key="release_mbid",
            )
        except Exception:
            current_app.logger.error(
                "Error generating cover art for MusicBrainz release collection:",
                exc_info=True,
            )
            payload["cover_art"] = None
    else:
        payload["cover_art"] = None

    return payload


def _serialize_release_collection_flattened_payload(
    collection, collection_id: int, *, count: int, offset: int, mb_curs,
):
    """Flatten release collection releases into recordings for playlist import."""
    track_count = _fetch_release_collection_flattened_track_count(mb_curs, collection_id)
    tracks = _fetch_release_collection_flattened_tracks(
        mb_curs,
        collection_id,
        count=count,
        offset=offset,
    )
    return {
        "collection": {
            "mbid": collection["collection_mbid"],
            "name": collection["name"],
            "public": bool(collection["public"]),
            "entity_type": collection["entity_type"],
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
                "release_mbid": t["release_mbid"],
                "release_name": t["release_name"],
            }
            for t in tracks
        ],
        "items": [],
        "cover_art": None,
    }


def fetch_collection_payload(
    collection_mbid: str,
    *,
    viewer_editor_id: int | None,
    count: int,
    offset: int,
    flatten_tracks: bool = False,
):
    """Fetch collection and items from the MusicBrainz database."""
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

            entity_type = collection["entity_type"]
            if entity_type not in SUPPORTED_COLLECTION_ENTITY_TYPES:
                return None, ({
                    "error": (
                        f"Collection type '{entity_type}' is not supported for import. "
                        "Only recording and release collections can be previewed."
                    )
                }, 400)

            collection_id = int(collection["collection_id"])
            if entity_type == "recording":
                payload = _serialize_recording_collection_payload(
                    collection, collection_id, count=count, offset=offset, mb_curs=mb_curs,
                )
            elif flatten_tracks:
                payload = _serialize_release_collection_flattened_payload(
                    collection, collection_id, count=count, offset=offset, mb_curs=mb_curs,
                )
            else:
                payload = _serialize_release_collection_payload(
                    collection, collection_id, count=count, offset=offset, mb_curs=mb_curs,
                )
    except Exception:
        current_app.logger.error("Error fetching MusicBrainz collection:", exc_info=True)
        return None, ({"error": "Failed to fetch collection from MusicBrainz. Please try again."}, 500)

    return payload, None


@collection_bp.get("/", defaults={"collection_mbid": ""})
@collection_bp.get("/<collection_mbid>/")
@web_musicbrainz_needed
def collection_page(collection_mbid: str):
    return render_template("index.html")


@collection_bp.route("/<collection_mbid>/", methods=["POST"])
@web_musicbrainz_needed
def load_collection(collection_mbid: str):
    """Load collection page data for React RouteLoader.

    Called by:
      Collection page RouteLoader, load-more, play-all, and save-as-playlist.
    """
    viewer_editor_id = None
    if current_user.is_authenticated:
        viewer_editor_id = getattr(current_user, "musicbrainz_row_id", None)

    count = get_positive_param("count", DEFAULT_COLLECTION_TRACKS_PER_CALL)
    offset = get_non_negative_param("offset", 0)
    flatten_tracks = request.args.get("flatten") == "tracks"

    payload, error = fetch_collection_payload(
        collection_mbid,
        viewer_editor_id=viewer_editor_id,
        count=count,
        offset=offset,
        flatten_tracks=flatten_tracks,
    )
    if error:
        body, code = error
        return jsonify(body), code

    return jsonify(payload)

