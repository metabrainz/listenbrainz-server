from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from typing import Optional, List


class UserRecordingRecord(BaseModel):
    """ Each individual record for a user's recording stats
    """
    artist_name: constr(min_length=1)
    artist_mbids: List[constr(min_length=1)] = []
    recording_mbid: Optional[str]
    release_name: Optional[str]
    release_mbid: Optional[str]
    track_name: str
    listen_count: int
    # to add empty fields to stats API response, for compatibility
    artist_msid: Optional[str]
    recording_msid: Optional[str]
    release_msid: Optional[str]
