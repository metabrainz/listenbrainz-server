import uuid

import requests
from flask import current_app
from psycopg2.extras import execute_values
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import text

from listenbrainz import db
from brainzutils import musicbrainz_db

from listenbrainz.webserver.errors import APINotFound


def bulk_insert_loved_tracks(user_id: int, feedback: list[tuple[int, str]]):
    """ Insert loved tracks imported from LFM into feedback table """
    # delete existing feedback for given mbids and then import new in same transaction
    delete_query = """
               WITH entries(user_id, recording_mbid) AS (VALUES %s)
        DELETE FROM recording_feedback rf
              USING entries e
              WHERE e.user_id = rf.user_id
                AND e.recording_mbid::uuid = rf.recording_mbid
    """
    insert_query = """
        INSERT INTO recording_feedback (user_id, created, recording_mbid, score)
             VALUES %s
    """
    connection = db.engine.raw_connection()
    with connection.cursor() as cursor:
        execute_values(cursor, delete_query, [(mbid,) for ts, mbid in feedback], template=f"({user_id}, %s)")
        execute_values(cursor, insert_query, feedback, template=f"({user_id}, to_timestamp(%s), %s, 1)")
    connection.commit()


def load_recordings_from_tracks(track_mbids: list) -> dict[str, str]:
    """ Fetch recording mbids corresponding to track mbids. Last.FM uses tracks mbids in loved tracks endpoint
     but we use recording mbids in feedback table so need convert between the two. """
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


def fetch_lfm_feedback(lfm_user: str):
    """ Retrieve the loved tracks of a user from Last.FM api """
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
    if response.status_code == 404:
        raise APINotFound(f"Last.FM user with username '{lfm_user}' not found")
    response.raise_for_status()

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


def import_feedback(user_id: int, lfm_user: str) -> dict:
    """ Main entrypoint into importing a user's loved tracks from Last.FM into LB feedback table.

    This method first retrieves the entire list of loved tracks for a user from Last.FM, discards
    entries that do not have (track) mbid, invalid mbids or mbids missing from the database,
    converts the track mbid to a recording mbid and inserts loved feedback for those recording
    mbids into LB feedback table.

    Args:
         user_id: the listenbrainz user id of the user
         lfm_user: the last.fm username of the user

    Returns a dict having various counts associated with the import.
    """
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
