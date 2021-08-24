import pydantic

from datetime import datetime
from enum import Enum
from typing import Optional, List


class UserArtistRecord(pydantic.BaseModel):
    """ Each individual record for a user's artists

    Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_msid: Optional[str]
    artist_mbids: List[str] = []
    listen_count: int
    artist_name: str


class UserArtistStatRange(pydantic.BaseModel):
    """ Model for user's most listened-to artists for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    count: int
    artists: List[UserArtistRecord]


class UserArtistStatJson(pydantic.BaseModel):
    """ Model for the JSON stored in the statistics.user table's artist column
    """
    week: Optional[UserArtistStatRange]
    year: Optional[UserArtistStatRange]
    month: Optional[UserArtistStatRange]
    all_time: Optional[UserArtistStatRange]


class UserArtistStat(UserArtistStatJson):
    """ Model for stats around a user's most listened artists
    """
    user_id: int
    last_updated: datetime
