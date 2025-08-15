import zipfile
import ijson
import json
import os
import io
from datetime import datetime, timezone
from pathlib import Path

from listenbrainz.db import user as db_user
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_IMPORT, insert_payload
from listenbrainz.webserver.models import SubmitListenUserMetadata
from werkzeug.exceptions import InternalServerError, ServiceUnavailable
from listenbrainz.domain.external_service import ExternalServiceError

from flask import current_app
from sqlalchemy import text

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

BATCH_SIZE = 1000
FILE_SIZE_LIMIT = 524288000  # 500 MB
IMPORTER_NAME = "ListenBrainz Archive Importer"


def initialize_spotify():
    client_credentials_manager = SpotifyClientCredentials(
        client_id=current_app.config["SPOTIFY_CLIENT_ID"],
        client_secret=current_app.config["SPOTIFY_CLIENT_SECRET"]
    )
    sp = spotipy.Spotify(auth_manager=client_credentials_manager)
    return sp


def get_spotify_data_from_cache(ts_conn, spotify_track_ids) -> dict:
    """ Get Spotify track data from cache for multiple track IDs.  """
    if not spotify_track_ids:
        return {}

    query = """
            SELECT t.track_id AS track_id
                 , t.name AS track_name
                 , t.track_number
                 , t.data->'duration_ms' AS duration_ms
                 , al.album_id AS album_id
                 , al.name AS album_name
                 , aal.artist_name AS album_artist_name
                 , aal.artist_ids AS album_artist_ids
                 , tal.artist_name AS artist_name
                 , tal.artist_ids AS artist_ids
             FROM spotify_cache.track t
             JOIN spotify_cache.album al
               ON t.album_id = al.album_id
        LEFT JOIN LATERAL (
                    SELECT array_agg(aa.artist_id ORDER BY raa.position) AS artist_ids
                         , string_agg(aa.name, ', 'ORDER BY raa.position) AS artist_name
                      FROM spotify_cache.rel_album_artist raa
                      JOIN spotify_cache.artist aa
                        ON raa.artist_id = aa.artist_id
                     WHERE raa.album_id = al.album_id
                  ) aal
               ON TRUE
        LEFT JOIN LATERAL (
                    SELECT array_agg(ta.artist_id ORDER BY rta.position) AS artist_ids
                         , string_agg(ta.name, ', 'ORDER BY rta.position) AS artist_name
                      FROM spotify_cache.rel_track_artist rta
                      JOIN spotify_cache.artist ta
                        ON rta.artist_id = ta.artist_id
                     WHERE rta.track_id = t.track_id
                  ) tal
               ON TRUE
            WHERE t.track_id = ANY(:track_ids);
            """
    result = ts_conn.execute(text(query), {"track_ids": spotify_track_ids})
    return {r.track_id: dict(r) for r in result}


def get_spotify_data_from_api(sp, spotify_track_ids) -> dict:
    """ Get Spotify track data from the API for multiple track IDs. """
    if not spotify_track_ids:
        return {}

    results = {}
    for i in range(0, len(spotify_track_ids), 50):
        batch = spotify_track_ids[i : i + 50]
        try:
            tracks = sp.tracks(batch)
            for track in tracks.get("tracks", []):
                if not track:
                    continue

                track_id = track["id"]

                artist_ids, artist_names = [], []
                for artist in track["artists"]:
                    artist_ids.append(artist["id"])
                    artist_names.append(artist["name"])

                album = track["album"]
                album_artists = album.get("artists")
                album_artist_ids, album_artist_names = [], []
                for artist in album_artists:
                    album_artist_ids.append(artist["id"])
                    album_artist_names.append(artist["name"])

                results[track_id] = {
                    "track_id": track_id,
                    "track_name": track["name"],
                    "track_number": track.get("track_number"),
                    "duration_ms": track.get("duration_ms"),
                    "album_id": album["id"],
                    "album_name": album["name"],
                    "album_artist_name": ", ".join(album_artist_names),
                    "album_artist_ids": album_artist_ids,
                    "artist_name": ", ".join(artist_names),
                    "artist_ids": artist_ids,
                }
        except Exception as e:
            current_app.logger.error(f"Error fetching Spotify tracks {batch}: {str(e)}", exc_info=True)

    return results


def get_spotify_data(ts_conn, sp: spotipy.Spotify, spotify_track_ids: set[str]) -> dict:
    tracks = get_spotify_data_from_cache(ts_conn, list(spotify_track_ids))
    remaining_track_ids = spotify_track_ids - set(tracks.keys())
    if remaining_track_ids:
        api_tracks = get_spotify_data_from_api(sp, list(remaining_track_ids))
        tracks.update(api_tracks)
    return tracks


def parse_spotify_listen(batch, ts_conn, sp):
    items = []
    for item in batch:
        try:
            items.append({
                "artist_name": item.get("master_metadata_album_artist_name"),
                "track_name": item.get("master_metadata_track_name"),
                "timestamp": int(item["timestamp"].timestamp()),
                "spotify_track_id": item["spotify_track_uri"].split(":")[2],
                "ms_played": item.get("ms_played"),
                "release_name": item.get("master_metadata_album_name", ""),
            })
        except:
            continue

    if not items:
        return []

    spotify_track_ids = {x["spotify_track_id"] for x in items}
    tracks = get_spotify_data(ts_conn, sp, spotify_track_ids)

    listens = []
    for item in items:
        sp_track = tracks.get(item["spotify_track_id"])
        if sp_track:
            track_metadata = {
                "artist_name": sp_track["artist_name"],
                "track_name": sp_track["track_name"],
                "release_name": sp_track["album_name"],
            }
            additional_info = {
                "tracknumber": sp_track["track_number"],
                "duration_ms": sp_track["duration_ms"],
                "spotify_artist_ids": [
                    f"https://open.spotify.com/artist/{artist_id}" for artist_id in sp_track["artist_ids"]
                ],
                "spotify_album_id": f"https://open.spotify.com/album/{sp_track['album_id']}",
                "spotify_album_artist_ids": [
                    f"https://open.spotify.com/artist/{artist_id}" for artist_id in sp_track["album_artist_ids"]
                ],
                "release_artist_name": sp_track["album_artist_name"],
            }
        elif item["artist_name"] and item["track_name"]:
            track_metadata = {
                "artist_name": item["artist_name"],
                "track_name": item["track_name"],
            }
            if item["release_name"]:
                track_metadata["release_name"] = item["release_name"]
            additional_info = {}
        else:
            continue

        additional_info.update({
            "ms_played": item["ms_played"],
            "origin_url": f"https://open.spotify.com/track/{item['spotify_track_id']}",
            "submission_client": IMPORTER_NAME,
            "music_service": "spotify.com"
        })
        track_metadata["additional_info"] = additional_info
        listens.append({
            "listened_at": item["timestamp"],
            "track_metadata": track_metadata,
        })
    return listens


def process_spotify_zip_file(db_conn, import_id, file_path, from_date, to_date):
    with zipfile.ZipFile(file_path, "r") as zip_file:
        if len(zip_file.namelist()) > 100:
            update_import_progress_and_status(db_conn, import_id, "failed", "Import failed due to an error")
            current_app.logger.error("Potential zip bomb attack")
            return

        audio_files = []
        for file in zip_file.namelist():
            filename = os.path.basename(file).lower()
            if filename.endswith(".json") and ("audio" in filename or "endsong" in filename):
                info = zip_file.getinfo(file)
            
                if info.file_size > FILE_SIZE_LIMIT:
                    update_import_progress_and_status(db_conn, import_id, "failed", "Import failed due to an error")
                    current_app.logger.error("Potential zip bomb attack")
                    return

                audio_files.append(file)

        for filename in audio_files:
            update_import_progress_and_status(db_conn, import_id, "in_progress", f"Importing {filename}")
            with zip_file.open(filename) as file, io.TextIOWrapper(file, encoding="utf-8") as contents:
                batch = []
                for entry in ijson.items(contents, "item"):
                    timestamp = datetime.strptime(
                        entry["ts"], "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc)
                    if from_date <= timestamp <= to_date:
                        entry["timestamp"] = timestamp
                        batch.append(entry)
                    if len(batch) == BATCH_SIZE:
                        yield batch
                        batch = []
                if batch:
                    yield batch
                    

def submit_listens(db_conn, listens, user_id, username, import_id):
    user_metadata = SubmitListenUserMetadata(user_id=user_id, musicbrainz_id=username)
    retries = 10
    while retries >= 0:
        try:
            current_app.logger.debug("Submitting %d listens for user %s", len(listens), username)
            insert_payload(listens, user_metadata, listen_type=LISTEN_TYPE_IMPORT)
            break
        except (InternalServerError, ServiceUnavailable):
            retries -= 1
            current_app.logger.error("ISE while trying to import listens for %s:", username, exc_info=True)
            if retries == 0:
                update_import_progress_and_status(db_conn, import_id, "failed", "Import failed due to an error")
                raise ExternalServiceError("ISE while trying to import listens")


def import_spotify_listens(db_conn, ts_conn, file_path, from_date, to_date, user_id, username, import_id):
    sp = initialize_spotify()
    for batch in process_spotify_zip_file(db_conn, import_id, file_path, from_date, to_date):
        parsed_listens = parse_spotify_listen(batch, ts_conn, sp)
        submit_listens(db_conn, parsed_listens, user_id, username, import_id)


def update_import_progress_and_status(db_conn, import_id, status, progress):
    """ Update progress for user data import """
    query = text("""
        UPDATE user_data_import
           SET metadata = metadata || (:metadata)::jsonb
         WHERE id = :import_id
    """)
    updated_metadata = {"status": status, "progress": progress}
    db_conn.execute(query, {
        "metadata": json.dumps(updated_metadata),
        "import_id": import_id
    })
    db_conn.commit()


def import_listens(db_conn, ts_conn, user_id, bg_task_metadata):
    user = db_user.get(db_conn, user_id)
    if user is None:
        current_app.logger.error("User with id: %s does not exist, skipping import.", user_id)
        return
    import_id = bg_task_metadata["import_id"]

    result = db_conn.execute(text("""
        SELECT *
          FROM user_data_import
         WHERE id = :import_id
    """), {"import_id": import_id})
    import_task = result.first()
    if import_task is None:
        current_app.logger.error("No import with import_id: %s, skipping.", bg_task_metadata["import_id"])
        return

    metadata = import_task.metadata
    if metadata["status"] in {"cancelled", "failed"}:
        return

    file_path = import_task.file_path
    service = import_task.service

    update_import_progress_and_status(db_conn, import_id, "in_progress", "Importing user listens")

    if service == "spotify":
        import_spotify_listens(
            db_conn, ts_conn, file_path,
            from_date=import_task.from_date, to_date=import_task.to_date,
            user_id=user_id, username=user["musicbrainz_id"], import_id=import_id,
        )
    update_import_progress_and_status(db_conn, import_id, "completed", "Import completed!")
    cleanup_old_imports(db_conn)


def cleanup_old_imports(db_conn):
    """ Delete user data imports that have been completed, cancelled or failed """
    with db_conn.begin():
        result = db_conn.execute(text("""\
            SELECT *
              FROM user_data_import
             WHERE metadata->>'status' IN ('completed', 'cancelled', 'failed')
        """))
        files_to_delete = [row.file_path for row in result]

        # Delete old listening history files that are no longer required
        for path in files_to_delete:
            file_path = Path(path)
            current_app.logger.info("Removing file: %s", file_path)
            file_path.unlink(missing_ok=True)
