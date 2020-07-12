""" Models for user's daily activity statistics.
    The daily activity shows the number of listens submitted to ListenBrainz per hour in the last week.
"""
import pydantic

from datetime import datetime
from typing import Optional, List


class UserDailyActivityRecord(pydantic.BaseModel):
    """ Each individual record for user's daily activity contains the time range,
        timestamp for start and end of the time range and listen count.
    """
    time_range: str  # The hour and day for which number of listens is provided
    from_ts: int
    to_ts: int
    listen_count: int


class UserDailyActivityStatMessage(pydantic.BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    musicbrainz_id: str
    type: str
    from_ts: int
    to_ts: int
    daily_activity: List[UserDailyActivityRecord]


class UserDailyActivityStatJson(pydantic.BaseModel):
    """ Model for the JSON stored in the statistics.user table's daily_activity column
    """
    to_ts: int
    from_ts: int
    daily_activity: List[UserDailyActivityRecord]


class UserDailyActivityStat(UserListeningActivityStatJson):
    """ Model for stats around user's daily activity
    """
    user_id: int
    last_updated: datetime
