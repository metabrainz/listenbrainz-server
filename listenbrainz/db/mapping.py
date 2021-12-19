from typing import Iterable
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


def load_recordings_from_mapping(mbids: Iterable[str], msids: Iterable[str]):
    query = """
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
         WHERE recording_msid IN :msids
            OR recording_mbid IN :mbids
    """

    with timescale.engine.connect() as connection:
        result = connection.execute(text(query), mbids=tuple(mbids), msids=tuple(msids))
        rows = result.fetchall()

        mbid_rows = {row["recording_mbid"]: row for row in rows if row["recording_mbid"] in mbids}
        msid_rows = {row["recording_msid"]: row for row in rows if row["recording_msid"] in msids}

        return mbid_rows, msid_rows
