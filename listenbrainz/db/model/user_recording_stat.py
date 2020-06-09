import pydantic

from datetime import datetime
from typing import Optional, List


class UserRecordingRecord(pydantic.BaseModel):
    """ Each individual record for a user's recording stats
    """
    artist_name: str
    artist_msid: Optional[str]
    artist_mbids: List[str] = []
    recording_mbid: Optional[str]
    recording_msid: Optional[str]
    release_name: Optional[str]
    release_mbid: Optional[str]
    release_msid: Optional[str]
    track_name: str
    listen_count: int


class UserRecordingStatRange(pydantic.BaseModel):
    """ Model for user's most listened-to recordings for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    count: int
    recordings: List[UserRecordingRecord]


class UserRecordingStatJson(pydantic.BaseModel):
    """ Model for the JSON stored in the statistics.user table's recording column
    """
    week: Optional[UserRecordingStatRange]
    year: Optional[UserRecordingStatRange]
    month: Optional[UserRecordingStatRange]
    all_time: Optional[UserRecordingStatRange]


class UserRecordingStat(pydantic.BaseModel):
    """ Model for stats around a user's most listened recordings
    """
    user_id: int
    recording: UserRecordingStatJson
    last_updated: datetime
