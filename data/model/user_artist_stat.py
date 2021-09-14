import pydantic

from datetime import datetime
from typing import Optional, List, Union

from data.model.user_recording_stat import UserRecordingRecord
from data.model.user_release_stat import UserReleaseRecord


class UserArtistRecord(pydantic.BaseModel):
    """ Each individual record for a user's artists

    Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_mbids: List[str] = []
    listen_count: int
    artist_name: str
    # to add an empty field to stats API response, for compatibility
    artist_msid: Optional[str]


# we need this so that we can call json(exclude_none=True) when inserting in the db
# not sure if this is necessary but preserving the old behaviour for now. json.dumps
# does not have an exclude_none option.
class UserArtistRecordList(pydantic.BaseModel):
    __root__: List[UserArtistRecord]


class UserArtistStatRange(pydantic.BaseModel):
    """ Model for user's most listened-to artists for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    count: int
    stats_range: str
    data: UserArtistRecordList


class UserArtistStat(UserArtistStatRange):
    """ Model for stats around a user's most listened artists
    """
    user_id: int
    last_updated: datetime
