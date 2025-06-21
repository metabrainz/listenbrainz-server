""" Models for user's genre trend statistics.
    The genre trend shows the distribution of music genres listened to by users 
    across different time brackets (00-06, 06-12, 12-18, 18-24) in last week/month/year.
"""
from pydantic import BaseModel, NonNegativeInt, constr


class GenreTrendRecord(BaseModel):
    """ Each individual record for user's genre trend contains the genre name,
        time bracket, and listen count for that genre during that time period.
    """
    genre: constr(min_length=1)
    time_bracket: constr(regex=r'^(00-06|06-12|12-18|18-24)$')
    listen_count: NonNegativeInt