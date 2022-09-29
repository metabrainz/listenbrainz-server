import uuid

import requests
from flask import current_app
from psycopg2.extras import execute_values
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import text

from listenbrainz import db
from brainzutils import musicbrainz_db


def bulk_insert_loved_tracks(user_id: int, feedback: list[tuple[int, str]]):
    # DO NOTHING because we can only import loved tracks.
    # if a user has imported something before from last.fm then the score doesn't change.
    # if the user has unloved a track on last.fm, we won't receive it this time so can't
    # remove it from feedback in any case.
    query = """
        INSERT INTO recording_feedback (user_id, created, recording_mbid, score)
             VALUES %s
        ON CONFLICT (user_id, recording_mbid)
         DO NOTHING
    """
    connection = db.engine.raw_connection()
    with connection.cursor() as cursor:
        execute_values(cursor, query, feedback, template=f"({user_id}, to_timestamp(%s), %s, 1)")
    connection.commit()


def load_recordings_from_tracks(track_mbids: list) -> dict[str, str]:
    query = """
        SELECT track.gid::text AS track_mbid
             , recording.gid::text AS recording_mbid
          FROM track
          JOIN recording
            ON track.recording = recording.id
         WHERE track.gid IN :tracks
    """
    with musicbrainz_db.engine.connect() as connection:
        result = connection.execute(text(query), {"tracks": tuple(track_mbids)})
        return {row["track_mbid"]: row["recording_mbid"] for row in result.mappings()}


def fetch_lfm_feedback(lfm_user):
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

    missing_mbid_count, invalid_mbid_count = 0, 0

    track_data = []
    track_mbids = []

    for page in range(1, total_pages + 1):
        params["page"] = page
        response = session.get(current_app.config["LASTFM_API_URL"], params=params)
        if response.status_code != 200:
            current_app.logger.error("Unable to import page %d for user %s: %s", page, lfm_user, response.text)
            continue

        tracks = response.json()["lovedtracks"]["track"]
        for track in tracks:
            if not track["mbid"]:
                missing_mbid_count += 1
                continue

            try:
                track_mbids.append(uuid.UUID(track["mbid"]))
                track_data.append((int(track["date"]["uts"]), track["mbid"]))
            except ValueError:
                invalid_mbid_count += 1
                continue

    counts = {
        "total": total_count,
        "missing_mbid": missing_mbid_count,
        "invalid_mbid": invalid_mbid_count
    }

    return track_mbids, track_data, counts


def import_feedback(user_id, lfm_user) -> dict:
    track_mbids, track_data, counts = fetch_lfm_feedback(lfm_user)
    recordings = load_recordings_from_tracks(track_mbids)

    recording_feedback = []
    mbid_not_found_count = 0

    for track in track_data:
        recording_mbid = recordings.get(track[1])
        if not recording_mbid:
            mbid_not_found_count += 1
            continue
        recording_feedback.append((track[0], recording_mbid))

    counts["mbid_not_found"] = mbid_not_found_count

    bulk_insert_loved_tracks(user_id, recording_feedback)
    counts["inserted"] = len(recording_feedback)

    return counts
