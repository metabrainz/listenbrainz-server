import psycopg2
import psycopg2.extras

from listenbrainz.db import timescale
from listenbrainz.db.model.metadata import RecordingMetadata
from typing import List
from flask import current_app

MAX_NUMBER_OF_RECORDINGS_PER_CALL = 50

def get_metadata_for_recording(recording_mbid_list: List[str]) -> List[RecordingMetadata]:
    """ Get a list of recording Metadata objects for a given recording in descending order of their creation.
        The list of recordings cannot exceed `~db.metadata.MAX_NUMBER_OF_RECORDINGS_PER_CALL` per call.
        If the number of items exceeds this limit, ValueError will be raised. Data is sorted according
        to recording_mbid

        Args:
            recording_mbid_list: A list of recording_mbids to fetch metadata for

        Returns:
            A list of RecordingMetadata objects
    """

    recording_mbid_list = tuple(recording_mbid_list)
    if len(recording_mbid_list) > MAX_NUMBER_OF_RECORDINGS_PER_CALL:
        return ValueError("Too many recording mbids passed in.")

    query = """SELECT *
                 FROM mb_metadata_cache
                WHERE recording_mbid in %s
             ORDER BY recording_mbid"""

    conn = timescale.engine.raw_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (recording_mbid_list,))
        return [RecordingMetadata(**dict(row)) for row in curs.fetchall()]
