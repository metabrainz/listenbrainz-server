""" Models for user's listening activity statistics.
    The listening activity shows the number of listens submitted to ListenBrainz in the last week/month/year.
"""
import pydantic

from datetime import datetime
from typing import Optional, List


class UserListeningActivityRecord(pydantic.BaseModel):
    """ Each individual record for user's listening activity contains the time range,
        timestamp for start and end of the time range and listen count.
    """
    # The range for which listen count have been calculated
    # For weekly statistics this will be the day of the week i.e Monday, Tuesday...
    # For monthly statistics this will be the date, i.e 1, 2...
    # For yearly statistics this will be the month, i.e January, February...
    # For all_time this will be the year, i.e. 2002, 2003...
    time_range: str
    from_ts: int
    to_ts: int
    listen_count: int


class UserListeningActivityStatMessage(pydantic.BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    musicbrainz_id: str
    type: str
    stats_range: str  # The range for which the stats are calculated, i.e week, month, year or all_time
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
