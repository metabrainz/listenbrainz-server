""" Models for user's daily activity statistics.
    The daily activity shows the number of listens submitted to ListenBrainz per hour in last week/month/year.
"""
from pydantic import BaseModel, NonNegativeInt, constr

from typing import List


class UserDailyActivityRecord(BaseModel):
    """ Each individual record for user's daily activity contains the time range,
        timestamp for start and end of the time range and listen count.
    """
    day: constr(min_length=1)
    hour: NonNegativeInt
    listen_count: NonNegativeInt


class UserDailyActivityStatMessage(BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    musicbrainz_id: constr(min_length=1)
    type: constr(min_length=1)
    stats_range: constr(min_length=1)  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: NonNegativeInt
    to_ts: NonNegativeInt
    data: List[UserDailyActivityRecord]
