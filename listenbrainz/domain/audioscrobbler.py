import logging
import uuid

import requests
from flask import current_app
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import text

from brainzutils import musicbrainz_db

from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth
from listenbrainz.domain.importer_service import ImporterService
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.webserver.errors import APINotFound

logger = logging.getLogger(__name__)


def bulk_insert_loved_tracks(user_id: int, feedback: list[tuple[int, str]], column: str):
    """ Insert loved tracks imported from an audioscrobbler service into feedback table """
    # delete existing feedback for given mbids and then import new in same transaction
    delete_query = SQL("""
               WITH entries(user_id, {column}) AS (VALUES %s)
        DELETE FROM recording_feedback rf
              USING entries e
              WHERE e.user_id = rf.user_id
                AND e.{column}::uuid = rf.{column}
    """).format(column=Identifier(column))
    insert_query = SQL("""
        INSERT INTO recording_feedback (user_id, created, {column}, score)
             VALUES %s
    """).format(column=Identifier(column))
    with db_conn.connection.cursor() as cursor:
        execute_values(cursor, delete_query, [(mbid,) for ts, mbid in feedback], template=f"({user_id}, %s)")
        execute_values(cursor, insert_query, feedback, template=f"({user_id}, to_timestamp(%s), %s, 1)")
        db_conn.connection.commit()


def load_recordings_from_tracks(track_mbids: list) -> dict[str, str]:
    """ Fetch recording mbids corresponding to track mbids. Audioscrobbler services use track mbids
     in loved tracks endpoint but we use recording mbids in feedback table so need convert between the two. """
    if not track_mbids:
        return {}
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


def bulk_get_msids(connection, items):
    """ Fetch msids for all the specified items (recording, artist_credit) in batches. """
    query = """
        SELECT DISTINCT ON (key)
               lower(s.recording)  || '-' || lower(s.artist_credit) AS key
             , s.gid::text AS recording_msid
          FROM messybrainz.submissions s
         WHERE EXISTS(
                    SELECT 1
                      FROM (VALUES %s) AS t(track_name, artist_name)
                     WHERE lower(s.recording) = lower(t.track_name)
                       AND lower(s.artist_credit) = lower(t.artist_name)
               )
      ORDER BY key, s.submitted, recording_msid 
    """
    curs = connection.connection.cursor()
    result = execute_values(curs, query, [(x["track_name"], x["artist_name"]) for x in items], fetch=True)
    return {r[0]: r[1] for r in result}


class AudioscrobblerService(ImporterService):
    """ Base class for audioscrobbler-compatible services (Last.fm, Libre.fm) that support
    importing loved tracks as feedback into ListenBrainz. """

    def __init__(self, service: ExternalServiceType, api_url: str, api_key: str):
        super().__init__(service)
        self.api_url = api_url
        self.api_key = api_key

    def add_new_user(self, user_id: int, token: dict) -> bool:
        external_service_oauth.save_token(
            db_conn, user_id=user_id, service=self.service, access_token=None, refresh_token=None,
            token_expires_ts=None, record_listens=True, scopes=[], external_user_id=token["external_user_id"],
            latest_listened_at=token["latest_listened_at"]
        )
        return True

    def fetch_feedback(self, username: str):
        """ Retrieve the loved tracks of a user from the audioscrobbler-compatible API. """
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, allowed_methods=["GET"])))

        params = {
            "method": "user.getlovedtracks",
            "user": username,
            "format": "json",
            "api_key": self.api_key,
            "limit": 100
        }
        response = session.get(self.api_url, params=params)
        if response.status_code == 404:
            raise APINotFound(f"{self.service.value.capitalize()} user with username '{username}' not found")
        response.raise_for_status()

        data = response.json()["lovedtracks"]["@attr"]
        total_pages = int(data["totalPages"])
        total_count = int(data["total"])

        items = []

        for page in range(1, total_pages + 1):
            params["page"] = page
            response = session.get(self.api_url, params=params)
            if response.status_code != 200:
                current_app.logger.error("Unable to import page %d for user %s: %s", page, username, response.text)
                continue

            tracks = response.json()["lovedtracks"]["track"]
            for track in tracks:
                item: dict = {
                    "timestamp": int(track["date"]["uts"]),
                    "track_name": track["name"],
                    "artist_name": track["artist"]["name"]
                }

                try:
                    uuid.UUID(track["mbid"])
                    item["mbid"] = track["mbid"]
                except (ValueError, TypeError):
                    item["mbid"] = None

                items.append(item)

        return items, total_count

    def import_feedback(self, user_id: int, username: str):
        """ Import a user's loved tracks from an audioscrobbler-compatible service into the LB feedback table.

        This method retrieves the entire list of loved tracks for a user, converts track mbids
        to recording mbids, looks up msids for tracks without mbids, and inserts loved feedback.

        Args:
             user_id: the listenbrainz user id of the user
             username: the username on the external service

        Returns a dict having various counts associated with the import.
        """
        items, total_count = self.fetch_feedback(username)

        all_mbids = [x["mbid"] for x in items if x["mbid"]]
        recordings_from_tracks = load_recordings_from_tracks(all_mbids)

        items_with_mbids, items_without_mbids = [], []
        for item in items:
            if item["mbid"]:
                if item["mbid"] in recordings_from_tracks:
                    item["mbid"] = recordings_from_tracks[item["mbid"]]
                items_with_mbids.append(item)
            else:
                items_without_mbids.append(item)

        mbid_feedback = [(x["timestamp"], x["mbid"]) for x in items_with_mbids]

        msids_map = bulk_get_msids(ts_conn, items_without_mbids)
        for item in items_without_mbids:
            key = f"{item['track_name'].lower()}-{item['artist_name'].lower()}"
            item["msid"] = msids_map.get(key)
        msid_feedback = [(x["timestamp"], x["msid"]) for x in items_without_mbids if x["msid"]]

        bulk_insert_loved_tracks(user_id, mbid_feedback, "recording_mbid")
        bulk_insert_loved_tracks(user_id, msid_feedback, "recording_msid")

        return {
            "total": total_count,
            "imported": len(mbid_feedback) + len(msid_feedback),
        }
