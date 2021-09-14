import pydantic

from datetime import datetime
from typing import Optional, List


class UserReleaseRecord(pydantic.BaseModel):
    """ Each individual record for a user's release stats
    """
    artist_mbids: List[str] = []
    release_mbid: Optional[str]
    release_name: str
    listen_count: int
    artist_name: str
    # to add empty fields to stats API response, for compatibility
    artist_msid: Optional[str]
    release_msid: Optional[str]


# we need this so that we can call json(exclude_none=True) when inserting in the db
# not sure if this is necessary but preserving the old behaviour for now. json.dumps
# does not have an exclude_none option.
class UserReleaseRecordList(pydantic.BaseModel):
    __root__: List[UserReleaseRecord]


class UserReleaseStatRange(pydantic.BaseModel):
    """ Model for user's most listened-to releases for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    count: int
    stats_range: str
    data: UserReleaseRecordList


class UserReleaseStat(UserReleaseStatRange):
    """ Model for stats around a user's most listened releases
    """
    user_id: int
    last_updated: datetime
