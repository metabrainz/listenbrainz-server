from typing import List, Optional
import uuid

from sqlalchemy import text

from listenbrainz.db.model.mbid_manual_mapping import MbidManualMapping
from listenbrainz.db import timescale as ts

def create_mbid_manual_mapping(mapping: MbidManualMapping):
    """Save a user mapping to the database. """
    query = """
        INSERT INTO mbid_manual_mapping(recording_msid, recording_mbid, user_id)
             VALUES (:recording_msid, :recording_mbid, :user_id)
        ON CONFLICT (user_id, recording_msid)
      DO UPDATE SET recording_mbid = EXCLUDED.recording_mbid
    """
    with ts.engine.begin() as conn:
        conn.execute(
            text(query),
            {
                "recording_msid": mapping.recording_msid,
                "recording_mbid": mapping.recording_mbid,
                "user_id": mapping.user_id
            }
        )

def get_mbid_manual_mapping(recording_msid: uuid.UUID, user_id: int) -> Optional[MbidManualMapping]:
    """Get a user's manual mbid mapping for a given recording
    
    Arguments:
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
    with ts.engine.begin() as conn:
        result = conn.execute(
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

def get_mbid_manual_mappings(recording_msid: uuid.UUID) -> List[MbidManualMapping]:
    """Get all manual mbid mappings for a given recording
    
    Arguments:
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
    with ts.engine.begin() as conn:
        result = conn.execute(
            text(query),
            {
                "recording_msid": recording_msid,
            }
        )
        return [MbidManualMapping(**row) for row in result.mappings()]
