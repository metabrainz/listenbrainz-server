import psycopg2
import psycopg2.extras

from listenbrainz.db import timescale
from listenbrainz.db.model.metadata import RecordingMetadata, ArtistMetadata, ReleaseGroupMetadata
from typing import List

MAX_NUMBER_OF_ENTITIES_PER_CALL = 50


def fixup_mbids_to_artists(row):
    """ Add artist mbid to the artists data retrieved from recording or release group cache """
    for (mbid, artist) in zip(row["artist_mbids"], row["artist_data"]["artists"]):
        artist["artist_mbid"] = str(mbid)
    return row


def get_metadata_for_recording(recording_mbid_list: List[str]) -> List[RecordingMetadata]:
    """ Get a list of recording Metadata objects for a given recording in descending order of their creation.
        The list of recordings cannot exceed `~db.metadata.MAX_NUMBER_OF_ENTITIES_PER_CALL` per call.
        If the number of items exceeds this limit, ValueError will be raised. Data is sorted according
        to recording_mbid

        Args:
            recording_mbid_list: A list of recording_mbids to fetch metadata for

        Returns:
            A list of RecordingMetadata objects
    """

    recording_mbid_list = tuple(recording_mbid_list)
    if len(recording_mbid_list) > MAX_NUMBER_OF_ENTITIES_PER_CALL:
        raise ValueError("Too many recording mbids passed in.")

    query = """SELECT *
                 FROM mapping.mb_metadata_cache
                WHERE recording_mbid in %s
             ORDER BY recording_mbid"""

    conn = timescale.engine.raw_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (recording_mbid_list, ))
        data = []
        for row in curs.fetchall():
            row = fixup_mbids_to_artists(row)
            data.append(RecordingMetadata(**row))
        return data


def get_metadata_for_release_group(release_group_mbid_list: List[str]) -> List[ReleaseGroupMetadata]:
    """ Get a list of release_group Metadata objects for a given release_group in descending order of their creation.
        The list of release groups cannot exceed `~db.metadata.MAX_NUMBER_OF_ENTITIES_PER_CALL` per call.
        If the number of items exceeds this limit, ValueError will be raised. Data is sorted according
        to release_group_mbid

        Args:
            release_group_mbid_list: A list of release_group_mbids to fetch metadata for

        Returns:
            A list of ReleaseGroupMetadata objects
    """

    release_group_mbid_list = tuple(release_group_mbid_list)
    if len(release_group_mbid_list) > MAX_NUMBER_OF_ENTITIES_PER_CALL:
        raise ValueError("Too many recording mbids passed in.")

    query = """SELECT *
                 FROM mapping.mb_release_group_cache
                WHERE release_group_mbid in %s
             ORDER BY release_group_mbid"""

    conn = timescale.engine.raw_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (release_group_mbid_list, ))
        data = []
        for row in curs.fetchall():
            row = fixup_mbids_to_artists(row)
            data.append(ReleaseGroupMetadata(**row))
        return data


def get_metadata_for_artist(artist_mbid_list: List[str]) -> List[ArtistMetadata]:
    """ Get a list of artist Metadata objects for a given recording in descending order of their creation.
        The list of artists cannot exceed `~db.metadata.MAX_NUMBER_OF_ENTITIES_PER_CALL` per call.
        If the number of items exceeds this limit, ValueError will be raised. Data is sorted according
        to recording_mbid

        Args:
            artist_mbid_list: A list of recording_mbids to fetch metadata for

        Returns:
            A list of RecordingMetadata objects
    """

    artist_mbid_list = tuple(artist_mbid_list)
    if len(artist_mbid_list) > MAX_NUMBER_OF_ENTITIES_PER_CALL:
        raise ValueError("Too many artist mbids passed in.")

    query = """SELECT *
                 FROM mapping.mb_artist_metadata_cache
                WHERE artist_mbid in %s
             ORDER BY artist_mbid"""

    conn = timescale.engine.raw_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (artist_mbid_list, ))
        return [ArtistMetadata(**dict(row)) for row in curs.fetchall()]
