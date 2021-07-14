from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from datetime import datetime
from typing import Optional, List


class UserReleaseRecord(BaseModel):
    """ Each individual record for a user's release stats
    """
    artist_msid: Optional[str]
    artist_mbids: List[constr(min_length=1)] = []
    release_mbid: Optional[str]
    release_msid: Optional[str]
    release_name: str
    listen_count: NonNegativeInt
    artist_name: str

    _validate_uuids: classmethod = validator(
        "artist_msid",
        "release_mbid",
        "release_msid",
        allow_reuse=True
    )(check_valid_uuid)

    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)


class UserReleaseStatRange(BaseModel):
    """ Model for user's most listened-to releases for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: NonNegativeInt
    from_ts: NonNegativeInt
    count: NonNegativeInt
    releases: List[UserReleaseRecord]


class UserReleaseStatJson(BaseModel):
    """ Model for the JSON stored in the statistics.user table's release column
    """
    week: Optional[UserReleaseStatRange]
    year: Optional[UserReleaseStatRange]
    month: Optional[UserReleaseStatRange]
    all_time: Optional[UserReleaseStatRange]


class UserReleaseStat(UserReleaseStatJson):
    """ Model for stats around a user's most listened releases
    """
    user_id: NonNegativeInt
    last_updated: datetime
