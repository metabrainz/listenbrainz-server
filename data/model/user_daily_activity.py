""" Models for user's daily activity statistics.
    The daily activity shows the number of listens submitted to ListenBrainz per hour in last week/month/year.
"""
from pydantic import BaseModel, NonNegativeInt, constr


class DailyActivityRecord(BaseModel):
    """ Each individual record for user's daily activity contains the time range,
        timestamp for start and end of the time range and listen count.
    """
    day: constr(min_length=1)
    hour: NonNegativeInt
    listen_count: NonNegativeInt
