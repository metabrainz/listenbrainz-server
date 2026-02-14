from typing import List, Optional, Iterable
import uuid

from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal
from sqlalchemy import text

from listenbrainz.db.model.mbid_manual_mapping import MbidManualMapping


def create_mbid_manual_mapping(ts_conn, mapping: MbidManualMapping):
    """Save a user mapping to the database. """
    query = """
        INSERT INTO mbid_manual_mapping(recording_msid, recording_mbid, user_id)
             VALUES (:recording_msid, :recording_mbid, :user_id)
        ON CONFLICT (user_id, recording_msid)
      DO UPDATE SET recording_mbid = EXCLUDED.recording_mbid
               , is_unlinked = FALSE
    """
    ts_conn.execute(
        text(query),
        {
            "recording_msid": mapping.recording_msid,
            "recording_mbid": mapping.recording_mbid,
            "user_id": mapping.user_id
        }
    )
    ts_conn.commit()


def create_mbid_manual_unlink(ts_conn, recording_msid: uuid.UUID, user_id: int):
    """Save an 'unlink' entry for a user -- the user wants to remove the MB mapping for this recording MSID.

    This inserts a row with a sentinel recording_mbid and is_unlinked=TRUE. The sentinel
    is used because recording_mbid has a NOT NULL constraint. If the user later re-links
    using create_mbid_manual_mapping, the ON CONFLICT clause will overwrite is_unlinked
    back to FALSE and set the real MBID.

    Arguments:
        ts_conn: timescale database connection
        recording_msid: the msid of the recording to unlink
        user_id: the user id performing the unlink
    """
    query = """
        INSERT INTO mbid_manual_mapping(recording_msid, recording_mbid, user_id, is_unlinked)
             VALUES (:recording_msid, '00000000-0000-0000-0000-000000000000', :user_id, TRUE)
        ON CONFLICT (user_id, recording_msid)
      DO UPDATE SET recording_mbid = EXCLUDED.recording_mbid
               , is_unlinked = TRUE
    """
    ts_conn.execute(
        text(query),
        {
            "recording_msid": str(recording_msid),
            "user_id": user_id
        }
    )
    ts_conn.commit()


def get_mbid_manual_mapping(ts_conn, recording_msid: uuid.UUID, user_id: int) -> Optional[MbidManualMapping]:
    """Get a user's manual mbid mapping for a given recording
    
    Arguments:
        ts_conn: timescale database connection
        recording_msid: the msid of the recording to get the mapping for
        user_id: the user id to get the mapping for

    Returns:
        An MbidManualMapping, or None if there is no mapping
    """
    query = """
        SELECT recording_msid::text
             , recording_mbid::text
             , user_id
             , created
          FROM mbid_manual_mapping
         WHERE recording_msid = :recording_msid
           AND user_id = :user_id
    """
    result = ts_conn.execute(
        text(query),
        {
            "recording_msid": recording_msid,
            "user_id": user_id
        }
    )
    row = result.fetchone()
    if row:
        return MbidManualMapping(
            recording_msid=row.recording_msid,
            recording_mbid=row.recording_mbid,
            user_id=row.user_id,
            created=row.created
        )
    else:
        return None


def get_mbid_manual_mappings(ts_conn, recording_msid: uuid.UUID) -> List[MbidManualMapping]:
    """Get all manual mbid mappings for a given recording
    
    Arguments:
        ts_conn: timescale database connection
        recording_msid: the msid of the recording to get the mapping for

    Returns:
        A list of MbidManualMapping objects, or an empty list if there are no mappings
    """
    query = """
        SELECT recording_msid::text
             , recording_mbid::text
             , user_id
             , created
          FROM mbid_manual_mapping
         WHERE recording_msid = :recording_msid
    """
    result = ts_conn.execute(text(query), {"recording_msid": recording_msid})
    ts_conn.commit()
    return [MbidManualMapping(**row) for row in result.mappings()]


def check_manual_mapping_exists(ts_conn, user_id: int, recording_msids: Iterable[str]) -> set[str]:
    """Check if a user has a mapping for a list of recordings

    Arguments:
        ts_conn: timescale database connection
        user_id: LB user id of a user
        recording_msids: the msids of the recordings to check

    Returns:
        A set of msids for which the user has a mapping
    """
    query = SQL("""
        SELECT t.msid
          FROM mbid_manual_mapping mmm
          JOIN (VALUES %s) AS t(msid)
            ON mmm.recording_msid = t.msid::uuid
         WHERE user_id = {user_id}
        """).format(user_id=Literal(user_id))
    with ts_conn.connection.cursor() as cursor:
        result = execute_values(cursor, query, [(msid,) for msid in recording_msids], fetch=True)
        return set(row[0] for row in result)
