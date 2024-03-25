import uuid
from typing import Iterable

import sqlalchemy
import sqlalchemy.exc
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz.db import timescale
from listenbrainz.messybrainz import exceptions


def submit_listens_and_sing_me_a_sweet_song(recordings):
    """ Inserts a list of recordings into MessyBrainz.

    Args:
        recordings: a list of recordings to be inserted
    Returns:
        A dict with key 'payload' and value set to a list of dicts containing the
        recording data for each inserted recording.
    """
    for r in recordings:
        if "artist" not in r or "title" not in r:
            raise exceptions.BadDataException("Require artist and title keys in submission")

    attempts = 0
    success = False
    while not success and attempts < 3:
        try:
            with timescale.engine.connect() as connection:
                data = insert_all_in_transaction(connection, recordings)
                success = True
        except sqlalchemy.exc.IntegrityError:
            # If we get an IntegrityError then our transaction failed.
            # We should try again
            pass

        attempts += 1

    if success:
        return data
    else:
        raise exceptions.ErrorAddingException("Failed to add data")


def insert_all_in_transaction(ts_conn, submissions: list[dict]):
    """ Inserts a list of recordings into MessyBrainz.

    Args:
        ts_conn: timescale database connection
        submissions: a list of recordings to be inserted
    Returns:
        A list of dicts containing the recording data for each inserted recording
    """
    ret = []
    for submission in submissions:
        result = submit_recording(
            ts_conn,
            submission["title"],
            submission["artist"],
            submission.get("release"),
            submission.get("track_number"),
            submission.get("duration")
        )
        ret.append(result)
    ts_conn.commit()
    return ret


def get_msid(connection, recording, artist, release=None, track_number=None, duration=None):
    """ Retrieve the msid for a (recording, artist, release, track_number, duration) tuple if present in the db. If
     there are duplicates in the table, the earliest submitted MSID will be returned.
    """
    query = text("""
        SELECT gid::TEXT
          FROM messybrainz.submissions
         WHERE lower(recording) = lower(:recording)
           AND lower(artist_credit) = lower(:artist_credit)
           -- NULL = NULL is NULL and not true so we need to handle NULLABLE fields separately
           AND ((lower(release) = lower(:release)) OR (release IS NULL AND :release IS NULL))
           AND ((lower(track_number) = lower(:track_number)) OR (track_number IS NULL AND :track_number IS NULL))
           AND ((duration = :duration) OR (duration IS NULL AND :duration IS NULL))
           -- historically, different set of fields have been used in calculating msids. therefore, the data imported
           -- from old MsB has duplicates when looked at from the current set of fields. we cannot delete such
           -- duplicates from the table easily (at least need to update all occurences of such MSIDs in all places
           -- MSIDs are used in LB). therefore to be consistent in future lookups, return the earliest submitted MSID
           -- of all matching ones
      ORDER BY submitted
         LIMIT 1   
    """)
    result = connection.execute(query, {
        "recording": recording,
        "artist_credit": artist,
        "release": release,
        "track_number": track_number,
        "duration": duration
    })
    row = result.fetchone()
    return row.gid if row else None


def submit_recording(connection, recording, artist, release=None, track_number=None, duration=None):
    """ Submits a new recording to MessyBrainz.

    Args:
        connection: the sqlalchemy db connection to execute queries with
        recording: recording name of the submitted listen
        artist: artist name of the submitted listen
        release: release name of the submitted listen
        track_number: track number of the recording of which the submitted listen is
        duration: the length of the track of which the submitted listen is in milliseconds

    Returns:
        the Recording MessyBrainz ID of the data
    """
    msid = get_msid(connection, recording, artist, release, track_number, duration)
    if msid:  # msid already exists in db
        return msid

    msid = uuid.uuid4()  # new msid
    query = text("""
        INSERT INTO messybrainz.submissions (gid, recording, artist_credit, release, track_number, duration)
             VALUES (:msid, :recording, :artist_credit, :release, :track_number, :duration)
    """)
    connection.execute(query, {
        "msid": msid,
        "recording": recording,
        "artist_credit": artist,
        "release": release,
        "track_number": track_number,
        "duration": duration
    })
    return str(msid)


def load_recordings_from_msids(ts_curs, messybrainz_ids: Iterable[str]) -> dict[str, dict]:
    """ Returns data for a recordings corresponding to a given list of MessyBrainz IDs.
    msids not found in the database are omitted from the returned dict (usually indicates the msid
    is wrong because data is not deleted from MsB).

    Args:
        messybrainz_ids: the MessyBrainz IDs of the recordings to fetch data for

    Returns:
        : a list of the recording data for the recordings in the order of the given MSIDs.
    """
    if not messybrainz_ids:
        return {}

    query = """
        WITH resolve_redirects AS (
            SELECT msid
                 , COALESCE(original_msid, msid::uuid) AS recording_msid
              FROM (VALUES %s) AS t(msid)
         LEFT JOIN messybrainz.submissions_redirect
                ON msid::uuid = duplicate_msid
        )
            SELECT msid
                 , recording AS title
                 , artist_credit AS artist
                 , release
                 , track_number
                 , duration
              FROM resolve_redirects
              JOIN messybrainz.submissions
                ON gid = recording_msid
    """
    results = execute_values(ts_curs, query, [(msid,) for msid in messybrainz_ids], fetch=True)
    return {row["msid"]: dict(row) for row in results}
