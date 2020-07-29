import pydantic

from datetime import datetime
from enum import Enum
from typing import Optional, List


class UserArtistMapRecord(pydantic.BaseModel):
    """ Each individual record for a user's artist map

    Contains the country_code and artist_count
    """
    country: str
    artist_count: int


class UserArtistMapStatRange(pydantic.BaseModel):
    """ Model for user's artist map for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    count: int
    artist_map: List[UserArtistMapRecord]
    last_updated: datetime


class UserArtistMapStatJson(pydantic.BaseModel):
    """ Model for the JSON stored in the statistics.user table's artist_map column
    """
    week: Optional[UserArtistMapStatRange]
    year: Optional[UserArtistMapStatRange]
    month: Optional[UserArtistMapStatRange]
    all_time: Optional[UserArtistMapStatRange]


class UserArtistMapStat(UserArtistMapStatJson):
    """ Model for stats around a user's most listened artists
    """
    user_id: int
    last_updated: datetime
