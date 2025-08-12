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
from sqlalchemy import text, bindparam, Integer, String

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

BATCH_SIZE = 1000

def initialize_spotify():
    client_credentials_manager = SpotifyClientCredentials( client_id = current_app.config['SPOTIFY_CLIENT_ID'], client_secret = current_app.config['SPOTIFY_CLIENT_SECRET'])
    sp = spotipy.Spotify(auth_manager = client_credentials_manager)
    return sp

def validate_spotify_listen(listen):
    return True # WIP

def parse_spotify_listen(batch, db_conn, ts_conn, sp):

    parsed_listens = []

    for listen in batch:
        if validate_spotify_listen(listen):
            artist = listen.get('master_metadata_album_artist_name', '')
            track_name = listen.get('master_metadata_track_name', '')
            listened_at = listen.get("ts")
            timestamp_dt = datetime.strptime(listened_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            unix_timestamp = timestamp_dt.timestamp()
            crafted_listen = {
                "listened_at": unix_timestamp,
                "track_metadata": {
                    "artist_name": artist,
                    "track_name": track_name,
                }
            }
            try:
                spotify_track_id = listen.get('spotify_track_uri').split(':')[2]
            except:
                return crafted_listen


            query = """
                    WITH
                        album_artists AS (
                            SELECT
                            raa.album_id,
                            json_agg(json_build_object(
                                'artist_id', a.artist_id,
                                'name', a.name,
                                'position', raa.position
                            ) ORDER BY raa.position) AS album_artist_list
                            FROM spotify_cache.rel_album_artist raa
                            JOIN spotify_cache.artist a ON raa.artist_id = a.artist_id
                            GROUP BY raa.album_id
                        ),

                        track_artists AS (
                            SELECT
                            rta.track_id,
                            json_agg(json_build_object(
                                'artist_id', a.artist_id,
                                'name', a.name,
                                'position', rta.position
                            ) ORDER BY rta.position) AS track_artist_list
                            FROM spotify_cache.rel_track_artist rta
                            JOIN spotify_cache.artist a ON rta.artist_id = a.artist_id
                            GROUP BY rta.track_id
                        )

                        SELECT
                        t.track_id,
                        t.name AS track_name,
                        t.track_number,
                        t.data AS track_data,

                        al.album_id,
                        al.name AS album_name,
                        al.type AS album_type,
                        al.release_date,
                        al.data AS album_data,

                        aa.album_artist_list,
                        ta.track_artist_list

                        FROM spotify_cache.track t
                        JOIN spotify_cache.album al ON t.album_id = al.album_id
                        LEFT JOIN album_artists aa ON al.album_id = aa.album_id
                        LEFT JOIN track_artists ta ON t.track_id = ta.track_id

                        WHERE t.track_id = :track_id;

                """
            result = ts_conn.execute(text(query), {
                "track_id": spotify_track_id,
            })
            spotify_track_info = result.first()
            
            if not spotify_track_info:
                if not sp:
                    current_app.logger.error(f"Can't retrieve metadata for the track {track_name}")
                    return
                spotify_track_info = spotify_web_api_track_info(sp, spotify_track_id)
                artists = spotify_track_info.get('artists')
                if artists:
                    if artists[0].get('name'):
                        artist = artists[0].get('name')
            else:
                artists = spotify_track_info.get('track_artist_list')
                if artists[0].get('name'):
                    artist = artists[0].get('name')
            
            crafted_listen['track_metadata']['artist_name'] = artist

            if not crafted_listen:
                current_app.logger.error("Failed to parse the listen: ", listen)
                continue
            current_app.logger.debug(str(type(crafted_listen)))
            parsed_listens.append(crafted_listen)
        else:
            current_app.logger.error("Failed to validate the listen: ", listen)
            continue
    
    return parsed_listens



def spotify_web_api_track_info(sp, track_id):
    track = sp.track(track_id)
    return track


def process_spotify_zip_file(db_conn, import_id, file_path, from_date, to_date):

    # Check for zip bomb attack
    with zipfile.ZipFile(file_path, 'r') as zip_file:
        if len(zip_file.namelist()) > 100:
            update_import_progress_and_status(db_conn, import_id, "failed", "Import failed due to an error")
            current_app.logger.error("Potential zip bomb attack")
            return
        
        audio_files = [
            file for file in zip_file.namelist()
            if 'audio' in os.path.basename(file).lower() and file.endswith('.json')
        ]

        for file in audio_files:
            info = zip_file.getinfo(file)
            
            if info.file_size > 524288000: # 500MB limit
                update_import_progress_and_status(db_conn, import_id, "failed", "Import failed due to an error")
                current_app.logger.error("Potential zip bomb attack")
                return

        
        current_app.logger.error(str(audio_files))
        for filename in audio_files:
            with zip_file.open(filename) as file:
                with io.TextIOWrapper(file, encoding='utf-8') as contents:
                    try:
                        batch = []
                        for entry in ijson.items(contents, 'item'):
                            timestamp = entry.get("ts")
                            timestamp_date = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                            if from_date <= timestamp_date <= to_date:
                                batch.append(entry)
                            if len(batch) == BATCH_SIZE:
                                batch = []
                                yield batch
                        if batch:
                            yield batch
                    except Exception as e:
                        current_app.logger.error(f"Error reading {filename}: {e}")
                        return
                    

def submit_listens(db_conn, listens, user_id, import_id):
    query = 'SELECT musicbrainz_id FROM "user" WHERE id = :user_id'
    result = db_conn.execute(text(query), {"user_id": user_id,})
    username = result.first().musicbrainz_id

    user_metadata = SubmitListenUserMetadata(user_id=user_id, musicbrainz_id=username)
    retries = 10
    while retries >= 0:
        try:
            current_app.logger.debug('Submitting %d listens for user %s', len(listens), username)
            insert_payload(listens, user_metadata, listen_type=LISTEN_TYPE_IMPORT)
            current_app.logger.debug('Submitted from importer!')
            break
        except (InternalServerError, ServiceUnavailable) as e:
            retries -= 1
            current_app.logger.error('ISE while trying to import listens for %s: %s', username, str(e))
            if retries == 0:
                update_import_progress_and_status(db_conn, import_id, "failed", "Import failed due to an error")
                raise ExternalServiceError('ISE while trying to import listens: %s', str(e))


def import_spotify_listens(db_conn, ts_conn, file_path, from_date, to_date, user_id, import_id):
    sp = initialize_spotify()
    for batch in process_spotify_zip_file(db_conn, import_id, file_path, from_date, to_date):
        parsed_listens = []
        if batch is None:
            update_import_progress_and_status(db_conn, import_id, "failed", "Import failed due to an error")
            current_app.logger.error("Error in processing the uploaded spotify listening history files!")
            return
        
        parsed_listens = parse_spotify_listen(batch, db_conn, ts_conn, sp)

        submit_listens(db_conn, parsed_listens, user_id, import_id)


def update_import_progress_and_status(db_conn, import_id, status, progress):
    """ Update progress for user data import """
    current_metadata = db_conn.execute(
        text("SELECT metadata FROM user_data_import WHERE id = :import_id"),
        {"import_id": import_id}
    ).scalar() or {}  

    updated_metadata = {**current_metadata, 'status': status, 'progress': progress}
    
    db_conn.execute(
        text("UPDATE user_data_import SET metadata = (:metadata)::jsonb WHERE id = :import_id"),
        {
            "metadata": json.dumps(updated_metadata),
            "import_id": import_id
        }
    )
    db_conn.commit()


def check_if_cancelled_or_failed(db_conn, import_id):
    """ Check if an import task was cancelled or failed """
    result = db_conn.execute(text("""
        SELECT metadata->>'status' FROM user_data_import WHERE id = :import_id
    """), {"import_id": import_id}).fetchone()
    if result is not None and (result[0] == 'cancelled' or result[0] == 'failed'):
        return True
    return False
    

def import_listens(db_conn, ts_conn, user_id, bg_task_metadata):
    #raise  ExternalServiceError("lets see")

    user = db_user.get(db_conn, user_id)
    if user is None:
        current_app.logger.error("User with id: %s does not exist, skipping import.", user_id)
        return
    

    result = db_conn.execute(text("""
        SELECT *
          FROM user_data_import
         WHERE id = :import_id
    """), {"import_id": bg_task_metadata["import_id"]})
    import_task = result.first()
    user_id = import_task.user_id
    if import_task is None:
        current_app.logger.error("No import with import_id: %s, skipping.", bg_task_metadata["import_id"])
        return

    import_id = import_task.id
    file_path = import_task.file_path
    service = import_task.service
    from_date = import_task.from_date
    try:
        from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    except:
        pass
    to_date = import_task.to_date
    try:
        to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    except:
        pass
    import_task_metadata = import_task.metadata


    update_import_progress_and_status(db_conn, import_id, "in_progress", "Importing user listens")

    if service == "spotify":
        if not check_if_cancelled_or_failed(db_conn, import_id):
            import_spotify_listens(db_conn, ts_conn, file_path, from_date, to_date, user_id, import_id)
        if not check_if_cancelled_or_failed(db_conn, import_id):
            update_import_progress_and_status(db_conn, import_id, "completed", "Import completed!")
            cleanup_old_imports(db_conn)
        


def cleanup_old_imports(db_conn):
    """ Delete user data imports that have been completed, cancelled or failed """
    with db_conn.begin():
        result = db_conn.execute(text("SELECT * FROM user_data_import WHERE metadata->>'status' IN ('completed', 'cancelled', 'failed')"))
        files_to_delete = [row.file_path for row in result]

        # Delete old listening history files that are no longer required
        for path in files_to_delete:
            file_path = Path(path)
            current_app.logger.info("Removing file: %s", file_path)
            file_path.unlink(missing_ok=True)
