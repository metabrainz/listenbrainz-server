import abc
import uuid

from flask import current_app
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import timescale


class BaseMsidMappingUpdater(abc.ABC):
    """ Base class for msid mapping updater """

    def __init__(self, table: str):
        """
            Args:
                table: name of the table to update
        """
        self.table = table

    def fetch_msids_query(self) -> str:
        """ Query to fetch msids from the update table. The query should return only 1 column and
         the column should be named recording_msid. """
        pass

    def update_msids_query(self):
        """ Query to update msids with corresponding mapped mbids. The query should accept the mapping as
         VALUES (recording_msid, recording_mbid) object.
        """
        pass

    def fetch_msids(self) -> list[uuid.UUID]:
        """ Fetch msids from the table to update. """
        query = self.fetch_msids_query()
        with db.engine.connect() as conn:
            result = conn.execute(text(query)).fetchall()
            return [row.recording_msid for row in result]

    def lookup_mbids_for_msids(self, msids: list[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
        """ Lookup mapped mbids for given msids """
        query = """
            SELECT recording_msid
                 , recording_mbid
              FROM mbid_mapping
              JOIN (VALUES %s) AS t(recording_msid)
             USING (recording_msid)
             WHERE recording_mbid IS NOT NULL
        """
        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                execute_values(curs, query, [(msid,) for msid in msids], page_size=len(msids))
                return {row[0]: row[1] for row in curs.fetchall()}
        finally:
            conn.close()

    def update_msids(self, mapping: dict[uuid.UUID, uuid.UUID]):
        """ Update msids with mapped mbids in the specified table. """
        query = self.update_msids_query()
        conn = db.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                execute_values(curs, query, mapping.items())
            conn.commit()
        finally:
            conn.close()

    def main(self):
        """ Main function to run the main msid update process """
        msids = self.fetch_msids()
        msids_count = len(msids)
        if msids_count == 0:
            current_app.logger.info("No msids to lookup for %s", self.table)
            return
        current_app.logger.info("Looking up %d msids for %s", msids_count, self.table)

        mapping = self.lookup_mbids_for_msids(msids)
        mapping_count = len(mapping)
        if mapping_count == 0:
            current_app.logger.info("No mbids found for given msids")
            return
        current_app.logger.info("Found %d msids to update", mapping_count)

        self.update_msids(mapping)


class ColumnMsidMappingUpdater(BaseMsidMappingUpdater):
    """ Updater for tables which have columns names recording msid and recording mbid """

    def fetch_msids_query(self) -> str:
        return f"SELECT DISTINCT recording_msid FROM {self.table} WHERE recording_mbid IS NULL"

    def update_msids_query(self) -> str:
        return f"""
              WITH mapping(recording_msid, recording_mbid) AS (VALUES %s)
            UPDATE {self.table} rf
               SET recording_mbid = m.recording_mbid
              FROM mapping m
             WHERE rf.recording_msid = m.recording_msid
        """


class JSONBMsidMappingUpdater(BaseMsidMappingUpdater):
    """ Updater for tables which have recording msid and recording mbid in a jsonb column """

    def fetch_msids_query(self) -> str:
        return f"""
            SELECT (metadata->>'recording_msid')::UUID AS recording_msid
              FROM user_timeline_event
             WHERE (metadata->>'recording_mbid') IS NULL
               AND (metadata->>'recording_msid') IS NOT NULL 
        """

    def update_msids_query(self) -> str:
        return f"""
              WITH mapping(recording_msid, recording_mbid) AS (VALUES %s)
            UPDATE user_timeline_event ute
               SET metadata = jsonb_set(metadata, '{{recording_mbid}}'::text[], to_jsonb(recording_mbid::text), true)
              FROM mapping m
             WHERE metadata->>'recording_msid' = m.recording_msid::text
        """


def run_all_updates():
    """ Check all tables having msids to update those with mbids from the mapping table """
    current_app.logger.info("Starting msid update process")

    feedback = ColumnMsidMappingUpdater("recording_feedback")
    feedback.main()

    pinned_recording = ColumnMsidMappingUpdater("pinned_recording")
    pinned_recording.main()

    user_timeline_event = JSONBMsidMappingUpdater("user_timeline_event")
    user_timeline_event.main()

    current_app.logger.info("Completed msid update process")
