""" Keep this file in sync with listenbrainz/db/models/user_listening_activity.py """
import pydantic

from datetime import datetime
from typing import Optional, List


class UserListeningActivityRecord(pydantic.BaseModel):
    """ Each individual record for user's listening activity

        Contains the time range, timestamp for start and end of the time range and listen count
    """
    time_range: str
    from_ts: int
    to_ts: int
    listen_count: int


class UserListeningActivityStatMessage(pydantic.BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    musicbrainz_id: str
    type: str
    range: str
    from_ts: int
    to_ts: int
    listening_activity: List[UserListeningActivityRecord]


class UserListeningActivityStatRange(pydantic.BaseModel):
    """ Model for user's listening activity for a particular time range.
        Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    listening_activity: List[UserListeningActivityRecord]


class UserListeningActivityStatJson(pydantic.BaseModel):
    """ Model for the JSON stored in the statistics.user table's listening_activity column
    """
    week: Optional[UserListeningActivityStatRange]
    month: Optional[UserListeningActivityStatRange]
    year: Optional[UserListeningActivityStatRange]
    all_time: Optional[UserListeningActivityStatRange]


class UserListeningActivityStat(UserListeningActivityStatJson):
    """ Model for stats around user's listening activity
    """
    user_id: int
    last_updated: datetime
