import pydantic

from datetime import datetime
from typing import Optional, List


class UserReleaseRecord(pydantic.BaseModel):
    """ Each individual record for a user's artists

    Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_msid: Optional[str]
    artist_mbids: List[str] = []
    release_mbid: Optional[str]
    release_msid: Optional[str]
    release_name: str
    listen_count: int
    artist_name: str


class UserReleaseStatRange(pydantic.BaseModel):
    """ Model for user's most listened-to artists for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    count: int
    releases: List[UserReleaseRecord]


class UserReleaseStatJson(pydantic.BaseModel):
    """ Model for the JSON stored in the statistics.user table's artist column
    """
    week: Optional[UserReleaseStatRange]
    year: Optional[UserReleaseStatRange]
    month: Optional[UserReleaseStatRange]
    all_time: Optional[UserReleaseStatRange]


class UserReleaseStat(pydantic.BaseModel):
    """ Model for stats around a user's most listened artists
    """
    user_id: int
    release: UserReleaseStatJson
    last_updated: datetime
