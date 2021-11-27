import sqlalchemy
from pydantic import BaseModel
from typing import List

from listenbrainz.db import timescale


class CBReviewMetadata(BaseModel):
    """ Model to represent the review payload sent to the CB api
    Some fields is_draft and license_choice are added by the backend
    and always the same. Hence, omitted from this model.
    """
    entity_type: str
    rating: int
    text: str
    entity_id: str
    language: str


class CBReviewTimelineMetadata(BaseModel):
    """Model to represent the data stored in user timeline event table
    for a CB review. We only store review uuid and the entity's mbid.
    Other data is retrieved from the CB api as needed.
    """
    review_id: str
    entity_id: str


def fetch_mapped_recording_data(mbids: List[str]):
    query = """
        SELECT artist_credit_name AS artist, recording_name AS title, release_name AS release,
               recording_mbid::TEXT, release_mbid::TEXT, artist_mbids::TEXT[]
          FROM mbid_mapping_metadata
         WHERE recording_mbid IN :mbids
    """
    # retrieves list of mbid's to fetch with
    with timescale.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), mbids=tuple(mbids))
        rows = result.fetchall()
        return { row["recording_mbid"]: row for row in rows } if rows else None
