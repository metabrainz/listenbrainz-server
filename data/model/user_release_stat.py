import pydantic

from datetime import datetime
from typing import Optional, List


class UserReleaseRecord(pydantic.BaseModel):
    """ Each individual record for a user's release stats
    """
    artist_msid: Optional[str]
    artist_mbids: List[str] = []
    release_mbid: Optional[str]
    release_msid: Optional[str]
    release_name: str
    listen_count: int
    artist_name: str


class UserReleaseStatRange(pydantic.BaseModel):
    """ Model for user's most listened-to releases for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    count: int
    releases: List[UserReleaseRecord]


class UserReleaseStatJson(pydantic.BaseModel):
    """ Model for the JSON stored in the statistics.user table's release column
    """
    week: Optional[UserReleaseStatRange]
    year: Optional[UserReleaseStatRange]
    month: Optional[UserReleaseStatRange]
    all_time: Optional[UserReleaseStatRange]


class UserReleaseStat(UserReleaseStatJson):
    """ Model for stats around a user's most listened releases
    """
    user_id: int
    last_updated: datetime
