import pydantic

from datetime import datetime
from typing import Optional, List


class UserRecordingRecord(pydantic.BaseModel):
    """ Each individual record for a user's recording stats
    """
    artist_name: str
    artist_mbids: List[str] = []
    recording_mbid: Optional[str]
    release_name: Optional[str]
    release_mbid: Optional[str]
    track_name: str
    listen_count: int
    # to add empty fields to stats API response, for compatibility
    artist_msid: Optional[str]
    recording_msid: Optional[str]
    release_msid: Optional[str]


# we need this so that we can call json(exclude_none=True) when inserting in the db
# not sure if this is necessary but preserving the old behaviour for now. json.dumps
# does not have an exclude_none option.
class UserRecordingRecordList(pydantic.BaseModel):
    __root__: List[UserRecordingRecord]


class UserRecordingStatRange(pydantic.BaseModel):
    """ Model for user's most listened-to recordings for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    count: int
    stats_range: str
    data: UserRecordingRecordList


class UserRecordingStat(UserRecordingStatRange):
    """ Model for stats around a user's most listened recordings
    """
    user_id: int
    last_updated: datetime
