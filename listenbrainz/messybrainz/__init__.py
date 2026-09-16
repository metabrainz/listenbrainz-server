import uuid
from typing import Iterable

import psycopg2
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
        A list of recording MSIDs in the same order as the given recordings.
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
        except (psycopg2.IntegrityError, sqlalchemy.exc.IntegrityError):
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
        A list of recording MSIDs in the same order as the given submissions
    """
    if not submissions:
        return []

    unique_submissions = []
    key_to_lookup_idx = {}
    keys = []
    for submission in submissions:
        key = _submission_key(submission)
        keys.append(key)
        if key not in key_to_lookup_idx:
            key_to_lookup_idx[key] = len(unique_submissions)
            unique_submissions.append(submission)

    existing_msids = _get_msids_for_submissions(ts_conn, unique_submissions)
    key_to_msid = {}
    insert_rows = []
    for key, idx in key_to_lookup_idx.items():
        msid = existing_msids.get(idx)
        if msid is None:
            submission = unique_submissions[idx]
            msid = str(uuid.uuid4())
            insert_rows.append((
                msid,
                submission["title"],
                submission["artist"],
                submission.get("release"),
                submission.get("track_number"),
                submission.get("duration")
            ))
        key_to_msid[key] = msid

    if insert_rows:
        query = """
            INSERT INTO messybrainz.submissions (gid, recording, artist_credit, release, track_number, duration)
                 VALUES %s
        """
        with ts_conn.connection.cursor() as curs:
            execute_values(curs, query, insert_rows, page_size=len(insert_rows))

    ts_conn.connection.commit()
    return [key_to_msid[key] for key in keys]


def _submission_key(submission: dict) -> tuple:
    """Return the case-insensitive lookup key used by MessyBrainz submissions.

    also duration is normalized to an int so that the in-batch dedup matches the
    database lookup.
    """
    return (
        submission["title"].lower(),
        submission["artist"].lower(),
        _lower_optional(submission.get("release")),
        _lower_optional(submission.get("track_number")),
        _int_optional(submission.get("duration"))
    )


def _lower_optional(value):
    return value.lower() if value is not None else None


def _int_optional(value):
    return int(value) if value is not None else None


def _get_msids_for_submissions(ts_conn, submissions: list[dict]) -> dict[int, str]:
    """Bulk lookup existing MSIDs for submissions, preserving earliest-submitted duplicates."""
    if not submissions:
        return {}

    query = """
        WITH incoming (idx, recording, artist_credit, release, track_number, duration) AS (VALUES %s)
        SELECT DISTINCT ON (incoming.idx)
               incoming.idx
             , submissions.gid::TEXT AS recording_msid
          FROM incoming
          JOIN messybrainz.submissions
            ON lower(submissions.recording) = lower(incoming.recording::TEXT)
           AND lower(submissions.artist_credit) = lower(incoming.artist_credit::TEXT)
           AND lower(submissions.release) IS NOT DISTINCT FROM lower(incoming.release::TEXT)
           AND lower(submissions.track_number) IS NOT DISTINCT FROM lower(incoming.track_number::TEXT)
           AND submissions.duration IS NOT DISTINCT FROM incoming.duration::INTEGER
      ORDER BY incoming.idx, submissions.submitted
    """
    values = [
        (
            idx,
            submission["title"],
            submission["artist"],
            submission.get("release"),
            submission.get("track_number"),
            submission.get("duration")
        )
        for idx, submission in enumerate(submissions)
    ]
    with ts_conn.connection.cursor() as curs:
        rows = execute_values(curs, query, values, fetch=True, page_size=len(values))
    return {row[0]: row[1] for row in rows}


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
