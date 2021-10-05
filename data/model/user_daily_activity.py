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
    musicbrainz_id: Optional[str]
    type: str
    stats_range: str  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: int
    to_ts: int
    data: List[UserDailyActivityRecord]
