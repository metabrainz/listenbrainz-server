import requests
from flask import current_app
from psycopg2.extras import execute_values
from requests import RequestException
from requests.adapters import HTTPAdapter, Retry
from typing import List, Dict, Tuple

from listenbrainz import db


def bulk_insert_loved_tracks(user_id: int, feedback: List[Tuple[int, str]]) -> int:
    query = """
        INSERT INTO recording_feedback (user_id, created, recording_mbid, score)
        VALUES %s ON CONFLICT (user_id, recording_mbid) DO NOTHING
    """
    with db.engine.raw_connection() as connection:
        cursor = connection.cursor()
        execute_values(cursor, query, feedback, template=f"({user_id}, %s, %s, 1)")
        return cursor.rowcount


def load_recordings_from_tracks(track_mbids: List[str]) -> Dict[str, str]:
    query = """
        SELECT track.gid AS track_mbid
             , recording.gid AS recording_mbid
          FROM track
          JOIN recording
            ON track.recording = recording.id
         WHERE track.gid IN :tracks   
    """
    with db.engine.connect() as connection:
        result = connection.execute(query, track_mbids)
        return {row["track_mbid"]: row["recording_mbid"] for row in result}


def import_feedback(user_id, lfm_user) -> Tuple[int, int]:
    response = None
    received_count, total_count = 0, 0

    try:
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, method_whitelist=["GET"])))

        params = {
            "method": "user.getlovedtracks",
            "user": lfm_user,
            "format": "json",
            "api_key": current_app.config["LASTFM_API_KEY"],
            "limit": 100
        }
        response = session.get(current_app.config["LASTFM_API_URL"], params=params)

        data = response.json()["lovedtracks"]["@attr"]
        total_pages = int(data["totalPages"])
        total_count = int(data["total"])
        received_count = 0

        for page in range(1, total_pages + 1):
            params["page"] = page
            response = session.get(current_app.config["LASTFM_API_URL"], params=params)
            if response.status_code != 200:
                current_app.logger.error("Unable to import page %d for user %s: %s", page, lfm_user, response.text)
                continue

            tracks = response.json()["lovedtracks"]["track"]
            track_data = []
            for track in tracks:
                if not track["mbid"]:
                     continue
                track_data.append((int(track["data"]["uts"]), track["mbid"]))

            recordings = load_recordings_from_tracks([track["mbid"] for track in tracks])
            recording_feedback = [(track[0], recordings[track[1]]) for track in track_data]
            received_count += bulk_insert_loved_tracks(user_id, recording_feedback)
    except RequestException:
        error_msg = response.text if response else None
        current_app.logger.error("Error while trying to revoke token for lfm user %s : %s",
                                 lfm_user, error_msg, exc_info=True)
    except Exception:
        current_app.logger.error("Error while importing bulk feedback:", exc_info=True)

    return received_count, total_count
