import time
import uuid
from typing import Iterable

import psycopg2
import sqlalchemy
import sqlalchemy.exc
from sqlalchemy import text, create_engine
from sqlalchemy.pool import NullPool

from listenbrainz.db import timescale
from listenbrainz.messybrainz import exceptions

engine = None


def init_db_connection(connect_str):
    global engine
    while True:
        try:
            engine = create_engine(connect_str, poolclass=NullPool)
            break
        except psycopg2.OperationalError as e:
            print("Couldn't establish connection to db: {}".format(str(e)))
            print("Sleeping for 2 seconds and trying again...")
            time.sleep(2)


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
            data = insert_all_in_transaction(recordings)
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


def insert_all_in_transaction(submissions: list[dict]):
    """ Inserts a list of recordings into MessyBrainz.

    Args:
        submissions: a list of recordings to be inserted
    Returns:
        A list of dicts containing the recording data for each inserted recording
    """
    ret = []
    with timescale.engine.begin() as ts_conn:
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


def load_recordings_from_msids(connection, messybrainz_ids: Iterable[str | uuid.UUID]):
    """ Returns data for a recordings corresponding to a given list of MessyBrainz IDs.
    msids not found in the database are omitted from the returned dict (usually indicates the msid
    is wrong because data is not deleted from MsB).

    Args:
        messybrainz_ids (list [uuid]): the MessyBrainz IDs of the recordings to fetch data for

    Returns:
        list [dict]: a list of the recording data for the recordings in the order of the given MSIDs.
    """
    if not messybrainz_ids:
        return {}

    messybrainz_ids = [str(msid) for msid in messybrainz_ids]

    query = text("""
        SELECT DISTINCT gid::TEXT AS msid, recording, artist_credit, release, track_number, duration
                   FROM messybrainz.submissions
                  WHERE gid IN :msids 
    """)
    result = connection.execute(query, {"msids": tuple(messybrainz_ids)})
    msid_recording_map = {x["msid"]: x for x in result.mappings()}

    # match results to every given msid so the list is returned in the same order
    results = []
    for msid in messybrainz_ids:
        if msid not in msid_recording_map:
            continue
        row = msid_recording_map[msid]
        results.append(row)

    return results
