""" Models for user's daily activity statistics.
    The daily activity shows the number of listens submitted to ListenBrainz per hour in last week/month/year.
"""
import pydantic

from datetime import datetime
from typing import Optional, List


class UserDailyActivityRecord(pydantic.BaseModel):
    """ Each individual record for user's daily activity contains the time range,
        timestamp for start and end of the time range and listen count.
    """
    day: str
    hour: int
    listen_count: int


class UserDailyActivityStatMessage(pydantic.BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    musicbrainz_id: str
    type: str
    stats_range: str  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: int
    to_ts: int
    daily_activity: List[UserDailyActivityRecord]


class UserDailyActivityStatRange(pydantic.BaseModel):
    """ Model for user's daily activity for a particular time range.
        Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    daily_activity: List[UserDailyActivityRecord]


class UserDailyActivityStatJson(pydantic.BaseModel):
    """ Model for the JSON stored in the statistics.user table's daily_activity column
    """
    week: Optional[UserDailyActivityStatRange]
    month: Optional[UserDailyActivityStatRange]
    year: Optional[UserDailyActivityStatRange]
    all_time: Optional[UserDailyActivityStatRange]


class UserDailyActivityStat(UserDailyActivityStatJson):
    """ Model for stats around user's daily activity
    """
    user_id: int
    last_updated: datetime
