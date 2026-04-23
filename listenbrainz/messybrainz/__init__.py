import uuid
from typing import Iterable

import sqlalchemy
import sqlalchemy.exc
import sentry_sdk
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
    with sentry_sdk.start_span(op="messybrainz", name="submit recordings to MessyBrainz") as span:
        span.set_data("recording_count", len(recordings))
        for r in recordings:
            if "artist" not in r or "title" not in r:
                raise exceptions.BadDataException("Require artist and title keys in submission")

        attempts = 0
        success = False
        while not success and attempts < 3:
            attempts += 1
            try:
                with sentry_sdk.start_span(op="db", name="insert recording batch into MessyBrainz") as insert_span:
                    insert_span.set_data("recording_count", len(recordings))
                    insert_span.set_data("attempt", attempts)
                    with timescale.engine.connect() as connection:
                        data = insert_all_in_transaction(connection, recordings)
                        success = True
            except sqlalchemy.exc.IntegrityError:
                # If we get an IntegrityError then our transaction failed.
                # We should try again
                pass

        span.set_data("attempts", attempts)
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
    if not submissions:
        return []

    def normalize_text(value):
        return value.lower() if value is not None else None

    def submission_key(submission):
        return (
            normalize_text(submission["title"]),
            normalize_text(submission["artist"]),
            normalize_text(submission.get("release")),
            normalize_text(submission.get("track_number")),
            submission.get("duration"),
        )

    keyed_submissions = []
    distinct_submissions = {}
    for submission in submissions:
        key = submission_key(submission)
        keyed_submissions.append(key)
        distinct_submissions.setdefault(key, submission)

    existing_args = [
        (recording, artist_credit, release, track_number, duration)
        for recording, artist_credit, release, track_number, duration in distinct_submissions.keys()
    ]
    existing_query = """
        SELECT input.recording
             , input.artist_credit
             , input.release
             , input.track_number
             , input.duration
             , matched.gid::text
          FROM (VALUES %s) AS input (recording, artist_credit, release, track_number, duration)
     LEFT JOIN LATERAL (
                SELECT gid
                  FROM messybrainz.submissions s
                 WHERE lower(s.recording) = input.recording
                   AND lower(s.artist_credit) = input.artist_credit
                   AND lower(s.release) IS NOT DISTINCT FROM input.release
                   AND lower(s.track_number) IS NOT DISTINCT FROM input.track_number
                   AND s.duration IS NOT DISTINCT FROM input.duration
              ORDER BY s.submitted
                 LIMIT 1
           ) matched ON TRUE
    """

    with sentry_sdk.start_span(op="db", name="resolve or insert MessyBrainz recordings") as span:
        span.set_data("recording_count", len(submissions))
        with sentry_sdk.start_span(op="db", name="lookup existing MessyBrainz recordings") as lookup_span:
            lookup_span.set_data("recording_count", len(existing_args))
            with ts_conn.connection.cursor() as curs:
                rows = execute_values(curs, existing_query, existing_args, page_size=len(existing_args), fetch=True)

        resolved_msids = {
            (recording, artist_credit, release, track_number, duration): msid
            for recording, artist_credit, release, track_number, duration, msid in rows
            if msid is not None
        }
        missing_keys = [key for key in distinct_submissions if key not in resolved_msids]
        span.set_data("existing_count", len(resolved_msids))
        span.set_data("missing_count", len(missing_keys))

        if missing_keys:
            insert_args = [
                (
                    str(uuid.uuid4()),
                    distinct_submissions[key]["title"],
                    distinct_submissions[key]["artist"],
                    distinct_submissions[key].get("release"),
                    distinct_submissions[key].get("track_number"),
                    distinct_submissions[key].get("duration"),
                )
                for key in missing_keys
            ]
            insert_query = """
                INSERT INTO messybrainz.submissions (gid, recording, artist_credit, release, track_number, duration)
                     VALUES %s
                 RETURNING gid::text
                         , lower(recording)
                         , lower(artist_credit)
                         , lower(release)
                         , lower(track_number)
                         , duration
            """
            with sentry_sdk.start_span(op="db", name="insert missing MessyBrainz recordings") as insert_span:
                insert_span.set_data("recording_count", len(insert_args))
                with ts_conn.connection.cursor() as curs:
                    inserted_rows = execute_values(curs, insert_query, insert_args, page_size=len(insert_args), fetch=True)
            for msid, recording, artist_credit, release, track_number, duration in inserted_rows:
                resolved_msids[(recording, artist_credit, release, track_number, duration)] = msid

        ret = [resolved_msids[key] for key in keyed_submissions]
    with sentry_sdk.start_span(op="db", name="commit MessyBrainz recording batch") as span:
        span.set_data("recording_count", len(ret))
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
