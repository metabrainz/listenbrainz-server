from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from datetime import datetime
from enum import Enum
from typing import Optional, List

class UserArtistRecord(BaseModel):
    """ Each individual record for a user's artists

    Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_msid: Optional[str]
    artist_mbids: List[constr(min_length=1)] = []
    listen_count: NonNegativeInt
    artist_name: str

    _validate_artist_msid: classmethod = validator("artist_msid", allow_reuse=True)(check_valid_uuid)
    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)

class UserArtistStatRange(BaseModel):
    """ Model for user's most listened-to artists for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: NonNegativeInt
    from_ts: NonNegativeInt
    count: NonNegativeInt
    artists: List[UserArtistRecord]


class UserArtistStatJson(BaseModel):
    """ Model for the JSON stored in the statistics.user table's artist column
    """
    week: Optional[UserArtistStatRange]
    year: Optional[UserArtistStatRange]
    month: Optional[UserArtistStatRange]
    all_time: Optional[UserArtistStatRange]


class UserArtistStat(UserArtistStatJson):
    """ Model for stats around a user's most listened artists
    """
    user_id: NonNegativeInt
    last_updated: datetime
