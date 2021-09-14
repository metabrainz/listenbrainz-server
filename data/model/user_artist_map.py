import pydantic

from datetime import datetime
from typing import Optional, List


class UserArtistMapRecord(pydantic.BaseModel):
    """ Each individual record for a user's artist map

    Contains the country_code and artist_count
    """
    country: str
    artist_count: int
    listen_count: Optional[int]  # Make field optional to maintain backward compatibility


class UserArtistMapRecordList(pydantic.BaseModel):
    __root__: List[UserArtistMapRecord]


class UserArtistMapStatRange(pydantic.BaseModel):
    """ Model for user's artist map for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    data: UserArtistMapRecordList
    stats_range: str


class UserArtistMapStat(UserArtistMapStatRange):
    """ Model for stats around a user's most listened artists
    """
    user_id: int
    last_updated: datetime
