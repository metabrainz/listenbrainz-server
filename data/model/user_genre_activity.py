""" Models for user's genre trend statistics.
    The genre trend shows the distribution of music genres listened to by users 
    across hourly time brackets in last week/month/year.
"""
from pydantic import BaseModel, NonNegativeInt, constr


class GenreActivityRecord(BaseModel):
    """ Each individual record for user's genre trend contains the genre name,
        time bracket, and listen count for that genre during that time period.
    """
    genre: constr(min_length=1)
    time_bracket: constr(regex=r'^(0[0-9]|1[0-9]|2[0-3])$')
    listen_count: NonNegativeInt