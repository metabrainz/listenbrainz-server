from pydantic import BaseModel, NonNegativeInt, constr

from datetime import datetime
from enum import Enum
from typing import Optional, List


class UserArtistMapRecord(BaseModel):
    """ Each individual record for a user's artist map

    Contains the country_code and artist_count
    """
    country: constr(min_length=1)
    artist_count: NonNegativeInt
    listen_count: Optional[NonNegativeInt]  # Make field optional to maintain backward compatibility


class UserArtistMapStatRange(BaseModel):
    """ Model for user's artist map for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: NonNegativeInt
    from_ts: NonNegativeInt
    artist_map: List[UserArtistMapRecord]
    last_updated: NonNegativeInt


class UserArtistMapStatJson(BaseModel):
    """ Model for the JSON stored in the statistics.user table's artist_map column
    """
    week: Optional[UserArtistMapStatRange]
    year: Optional[UserArtistMapStatRange]
    month: Optional[UserArtistMapStatRange]
    all_time: Optional[UserArtistMapStatRange]


class UserArtistMapStat(UserArtistMapStatJson):
    """ Model for stats around a user's most listened artists
    """
    user_id: NonNegativeInt
    last_updated: datetime
