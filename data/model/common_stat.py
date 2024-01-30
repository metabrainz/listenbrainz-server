# This file contains models for db -> api for statistics.

from datetime import datetime
from typing import TypeVar, Generic, Optional, List

from enum import Enum
from pydantic.generics import GenericModel


class StatisticsRange(Enum):
    this_week = 'this_week'
    this_month = 'this_month'
    this_year = 'this_year'
    week = 'week'
    month = 'month'
    quarter = 'quarter'
    year = 'year'
    half_yearly = 'half_yearly'
    all_time = 'all_time'


#: list of allowed value for range param accepted by various statistics endpoints
ALLOWED_STATISTICS_RANGE = [x.value for x in StatisticsRange]


StatT = TypeVar('StatT')


class StatRecordList(GenericModel, Generic[StatT]):
    """ Generic model with root type as list of given type.
    Can be used as part of another model where you want to call .json() just on the
    single member. Without the custom root type, an additional level of nesting will
    be added to the json and if we used List[StatT] in the models then we wouldn't be
    able to call .json() on a particular member as we do while inserting stats in the
    database using .json(exclude_none=True).
    """
    __root__: List[StatT]


class StatApi(GenericModel, Generic[StatT]):
    """ Generic base mode for representing a user/sitewide stat retrieved from the database and
    to send using the api."""
    user_id: int
    count: Optional[int]
    to_ts: int
    from_ts: int
    stats_range: str
    data: StatRecordList[StatT]
    last_updated: int
