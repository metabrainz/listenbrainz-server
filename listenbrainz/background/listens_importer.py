import zipfile
import ijson
import os
import io
from datetime import datetime

from listenbrainz.db import user as db_user
from listenbrainz.webserver.views.api_tools import insert_payload
from flask import current_app
from sqlalchemy import text

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

BATCH_SIZE = 100

def initialize_spotify():
    client_credentials_manager = SpotifyClientCredentials( client_id = current_app.config['SPOTIFY_CLIENT_ID'], client_secret = current_app.config['SPOTIFY_CLIENT_SECRET'])
    sp = spotipy.Spotify(auth_manager = client_credentials_manager)
    return sp

def validate_spotify_listen(listen):
    return True # WIP

def parse_spotify_listen(listen, db_conn, ts_conn, sp):

    artist = listen.get('master_metadata_album_artist_name', '')
    track_name = listen.get('master_metadata_track_name', '')
    crafted_listen = {
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
    
    crafted_listen['track_metadata']['artist'] = artist
    return crafted_listen
    
    


def spotify_web_api_track_info(sp, track_id):
    track = sp.track(track_id)
    return track


def process_spotify_zip_file(file_path, from_date, to_date):

    # Check for zip bomb attack
    with zipfile.ZipFile(file_path, 'r') as zip_file:
        if len(zip_file.namelist()) > 100:
            current_app.logger.error("Potential zip bomb attack")
            return
        
        audio_files = [
            file for file in zip_file.namelist()
            if 'audio' in os.path.basename(file).lower() and file.endswith('.json')
        ]

        for file in audio_files:
            info = zip_file.getinfo(file)
            
            if info.file_size > 524288000: # 500MB limit
                current_app.logger.error("Potential zip bomb attack")
                return

        
        for filename in audio_files:
            with zip_file.open(filename) as file:
                with io.TextIOWrapper(file, encoding='utf-8') as contents:
                    try:
                        batch = []
                        for entry in ijson.items(contents, 'item'):
                            timestamp = entry.get("ts")
                            timestamp_date = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").date()
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

def import_spotify_listens(file_path, from_date, to_date, db_conn, ts_conn):
    sp = initialize_spotify()
    for batch in process_spotify_zip_file(file_path, from_date, to_date):
        parsed_listens = []
        if batch is None:
            current_app.logger.error("Error in processing the uploaded spotify listening history files!")
            return
        for listen in batch:
            if validate_spotify_listen(listen):
                parsed_listen = parse_spotify_listen(listen, db_conn, ts_conn, sp)
                if not parsed_listen:
                    current_app.logger.error("Failed to parse the listen: ", listen)
                    continue
                parsed_listens.append(parsed_listen)
            else:
                current_app.logger.error("Failed to validate the listen: ", listen)
                continue
        #submit_listens(parsed_listens)



def import_listens(db_conn, ts_conn, user_id: int, bg_task_metadata):
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
    if import_task is None:
        current_app.logger.error("No import with import_id: %s, skipping.", bg_task_metadata["import_id"])
        return

    import_id = import_task.id
    file_path = import_task.file_path
    service = import_task.service
    from_date = import_task.from_date
    from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    to_date = import_task.to_date
    to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    import_task_metadata = import_task.metadata

    if service == "spotify":
        import_spotify_listens(file_path, from_date, to_date, db_conn, ts_conn)
            