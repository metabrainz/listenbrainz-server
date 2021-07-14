from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from datetime import datetime
from typing import Optional, List


class UserRecordingRecord(BaseModel):
    """ Each individual record for a user's recording stats
    """
    artist_name: str
    artist_msid: Optional[str]
    artist_mbids: List[constr(min_length=1)] = []
    recording_mbid: Optional[str]
    recording_msid: Optional[str]
    release_name: Optional[str]
    release_mbid: Optional[str]
    release_msid: Optional[str]
    track_name: str
    listen_count: NonNegativeInt

    _validate_uuids: classmethod = validator(
        "artist_msid",
        "recording_mbid",
        "recording_msid",
        "release_mbid",
        "release_msid",
        allow_reuse=True
    )(check_valid_uuid)

    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)


class UserRecordingStatRange(BaseModel):
    """ Model for user's most listened-to recordings for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: NonNegativeInt
    from_ts: NonNegativeInt
    count: NonNegativeInt
    recordings: List[UserRecordingRecord]


class UserRecordingStatJson(BaseModel):
    """ Model for the JSON stored in the statistics.user table's recording column
    """
    week: Optional[UserRecordingStatRange]
    year: Optional[UserRecordingStatRange]
    month: Optional[UserRecordingStatRange]
    all_time: Optional[UserRecordingStatRange]


class UserRecordingStat(UserRecordingStatJson):
    """ Model for stats around a user's most listened recordings
    """
    user_id: NonNegativeInt
    last_updated: datetime
