""" Models for user's genre trend statistics.
    The genre trend shows the distribution of music genres listened to by users 
    across hourly time brackets in last week/month/year.
"""
from pydantic import BaseModel, NonNegativeInt, constr, conint


class GenreActivityRecord(BaseModel):
    """ Each individual record for user's genre trend contains the genre name,
        time bracket, and listen count for that genre during that time period.
    """
    genre: constr(min_length=1)
    hour: conint(ge=0, le=23)
    listen_count: NonNegativeInt