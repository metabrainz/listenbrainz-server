# Script to fetch artist MBIDs from MusicBrainz Database using
# the recording MBIDs in the MessyBrainz database.

import brainzutils.musicbrainz_db.recording as mb_recording
import json

from brainzutils import musicbrainz_db
from brainzutils.musicbrainz_db.exceptions import NoDataFoundException
from messybrainz import db
from messybrainz import data
from sqlalchemy import text
import uuid


# lifted from AcousticBrainz
def is_valid_uuid(u):
    try:
        u = uuid.UUID(u)
        return True
    except ValueError:
        return False


def insert_artist_mbids(connection, recording_mbid, artist_mbids):
    """ Inserts the artist_mbids corresponding to the recording_mbids
        into the recording_artist table.
    """

    for artist_mbid in artist_mbids:
        query = text("""INSERT INTO recording_artist_join (recording_mbid, artist_mbid, updated)
                             VALUES (:recording_mbid, :artist_mbid, now())
        """)

        result = connection.execute(query, {
        "recording_mbid": recording_mbid,
        "artist_mbid": artist_mbid,
        })


def is_recording_mbid_present(connection, recording_mbid):
    """
        Check if recording MBID is already present in recording_artist table.
        Returns True if recording MBID is present else False is returned.
    """

    query = text("""SELECT recording_mbid
                      FROM recording_artist_join
                     WHERE recording_mbid = :recording_mbid
    """)

    result = connection.execute(query, {
    "recording_mbid": recording_mbid,
    })

    if result.rowcount:
        return True

    return False


def fetch_and_store_artist_mbids(connection, recording_mbid):
    """ Fetches artist MBIDs from the MusicBrainz database for the recording MBID.
        And inserts the artist MBIDs into the recording_artist table.
    """

    recording = mb_recording.get_recording_by_mbid(recording_mbid, includes=['artists'])

    artist_mbids = []
    for artist in recording['artists']:
        artist_mbids.append(artist['id'])

    insert_artist_mbids(connection, recording_mbid, artist_mbids)


def fetch_and_store_artist_mbids_for_all_recording_mbids(reset=False):
    """ Fetches artist MBIDs from the musicbrainz database for the recording MBIDs
        in the recording_json table submitted while submitting a listen.
        Returns the number of recording MBIDs that were processed and number of
        recording MBIDs that were added to the recording_artist table.
    """

    with db.engine.begin() as connection:
        if reset:
            query = text("""TRUNCATE TABLE recording_artist_join""")
            connection.execute(query)

        recording_mbids = data.fetch_distinct_recording_mbids(connection)
        num_recording_mbids_added = 0
        num_recording_mbids_processed = recording_mbids.rowcount
        for recording_mbid in recording_mbids:
            if is_valid_uuid(recording_mbid[0]):
                if not is_recording_mbid_present(connection, recording_mbid[0]):
                    try:
                        fetch_and_store_artist_mbids(connection, recording_mbid[0])
                        num_recording_mbids_added += 1
                    except NoDataFoundException:
                        pass

        return num_recording_mbids_processed, num_recording_mbids_added
