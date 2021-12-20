from typing import Iterable, Dict
from typing import Optional, Tuple

from pydantic import BaseModel, validator
from sqlalchemy import text

from data.model.validators import check_valid_uuid
from listenbrainz.db import timescale


class MsidMbidModel(BaseModel):
    """
    A model to use as base for tables which support both msid and mbids.

    We intend to migrate from msids to mbids but for compatibility and till
    the remaining gaps in mapping are filled we want to support msids as well.
    """
    recording_msid: Optional[str]
    recording_mbid: Optional[str]

    _validate_msids: classmethod = validator(
        "recording_msid",
        "recording_mbid",
        allow_reuse=True
    )(check_valid_uuid)


def load_recordings_from_mapping(mbids: Iterable[str], msids: Iterable[str]) -> Tuple[Dict, Dict]:
    """ Given a list of mbids and msids, returns two maps - one having mbid as key and the recording
    info as value and the other having the msid as key and recording info as value.
    """
    if not mbids and not msids:
        return {}, {}

    clauses = []
    if mbids:
        clauses.append("recording_mbid IN :mbids")
    if msids:
        clauses.append("recording_msid IN :msids")
    full_where_clause = " OR ".join(clauses)

    # direct string interpolation is susceptible to SQL injection
    # but here we are only adding where clauses with it. the actual
    # params are added using proper sqlalchemy quoting.
    query = f"""
        SELECT recording_msid::TEXT
             , recording_mbid::TEXT
             , release_mbid::TEXT
             , artist_mbids::TEXT[]
             , artist_credit_name AS artist
             , recording_name AS title
             , release_name AS release
          FROM mbid_mapping m
          JOIN mbid_mapping_metadata mm
         USING (recording_mbid)
         WHERE {full_where_clause}
    """

    with timescale.engine.connect() as connection:
        result = connection.execute(text(query), mbids=tuple(mbids), msids=tuple(msids))
        rows = result.fetchall()

        mbid_rows = {row["recording_mbid"]: dict(row) for row in rows if row["recording_mbid"] in mbids}
        msid_rows = {row["recording_msid"]: dict(row) for row in rows if row["recording_msid"] in msids}

        return mbid_rows, msid_rows
