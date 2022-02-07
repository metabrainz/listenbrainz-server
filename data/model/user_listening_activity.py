""" Models for user's listening activity statistics.
    The listening activity shows the number of listens submitted to ListenBrainz in the last week/month/year.
"""
from pydantic import BaseModel, NonNegativeInt, constr

from typing import List


class UserListeningActivityRecord(BaseModel):
    """ Each individual record for user's listening activity contains the time range,
        timestamp for start and end of the time range and listen count.
    """
    # The range for which listen count have been calculated
    # For weekly statistics this will be the day of the week i.e Monday, Tuesday...
    # For monthly statistics this will be the date, i.e 1, 2...
    # For yearly statistics this will be the month, i.e January, February...
    # For all_time this will be the year, i.e. 2002, 2003...
    time_range: constr(min_length=1)
    from_ts: NonNegativeInt
    to_ts: NonNegativeInt
    listen_count: NonNegativeInt


class UserListeningActivityStatMessage(BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    user_id: NonNegativeInt
    type: constr(min_length=1)
    stats_range: constr(min_length=1)  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: NonNegativeInt
    to_ts: NonNegativeInt
    data: List[UserListeningActivityRecord]


class SitewideListeningActivityStatMessage(BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    type: str
    stats_range: str  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: int
    to_ts: int
    data: List[UserListeningActivityRecord]
