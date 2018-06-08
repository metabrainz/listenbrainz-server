
import brainzutils.musicbrainz_db.recording as mb_recording
import json

from brainzutils import musicbrainz_db
from brainzutils.musicbrainz_db.exceptions import NoDataFoundException
from messybrainz import db
from messybrainz.db import data
from sqlalchemy import text


def insert_artist_mbids(connection, recording_mbid, artist_mbids):
    """ Inserts the artist_mbids corresponding to the recording_mbids
        into the recording_artist_join table.
    """

    query = text("""INSERT INTO recording_artist_join (recording_mbid, artist_mbid, updated)
                         VALUES (:recording_mbid, :artist_mbid, now())""")

    values = [
        {"recording_mbid": recording_mbid, "artist_mbid": artist_mbid} for artist_mbid in artist_mbids
    ]

    connection.execute(query, values)


def fetch_and_store_artist_mbids(connection, recording_mbid):
    """ Fetches artist MBIDs from the MusicBrainz database for the recording MBID.
        And inserts the artist MBIDs into the recording_artist_join table.
    """

    recording = mb_recording.get_recording_by_mbid(recording_mbid, includes=['artists'])

    artist_mbids = []
    for artist in recording['artists']:
        artist_mbids.append(artist['id'])

    insert_artist_mbids(connection, recording_mbid, artist_mbids)


def fetch_recording_mbids_not_in_recording_artist_join(connection):
    """ Fetches recording MBIDs that are present in recording_json table
        but are not present in recording_artist_join table and returns
        a list of those recording MBIDs.
    """

    query = text("""SELECT DISTINCT rj.data ->> 'recording_mbid'
                               FROM recording_json AS rj
                          LEFT JOIN recording_artist_join AS raj
                                 ON (rj.data ->> 'recording_mbid')::uuid = raj.recording_mbid
                              WHERE rj.data ->> 'recording_mbid' IS NOT NULL
                                AND raj.recording_mbid IS NULL
    """)

    result = connection.execute(query)

    return list(result.fetchall()[0])


def truncate_recording_artist_join():
    """Truncates the table recording_artist_join."""

    with db.engine.begin() as connection:
        query = text("""TRUNCATE TABLE recording_artist_join""")
        connection.execute(query)


def fetch_and_store_artist_mbids_for_all_recording_mbids():
    """ Fetches artist MBIDs from the musicbrainz database for the recording MBIDs
        in the recording_json table submitted while submitting a listen.
        Returns the number of recording MBIDs that were processed and number of
        recording MBIDs that were added to the recording_artist_join table.
    """

    with db.engine.begin() as connection:
        recording_mbids = fetch_recording_mbids_not_in_recording_artist_join(connection)
        num_recording_mbids_added = 0
        num_recording_mbids_processed = len(recording_mbids)
        for recording_mbid in recording_mbids:
            try:
                fetch_and_store_artist_mbids(connection, recording_mbid)
                num_recording_mbids_added += 1
            except NoDataFoundException:
                # While submitting recordings we don't check if the recording MBID
                # exists in MusicBrainz database. So, this exception can get raised if
                # recording MBID doesnot exist in MusicBrainz database and we tried to
                # query for it.
                pass

        return num_recording_mbids_processed, num_recording_mbids_added
