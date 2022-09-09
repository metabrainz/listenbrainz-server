# This file contains models for spark -> db statistics.
from typing import TypeVar, Generic, List, Optional

from pydantic import constr, NonNegativeInt, BaseModel
from pydantic.generics import GenericModel

SparkT = TypeVar("SparkT")


class UserStatRecords(GenericModel, Generic[SparkT]):
    user_id: NonNegativeInt
    data: List[SparkT]


class StatMessage(GenericModel, Generic[SparkT]):
    """ Format of messages sent to the ListenBrainz Server from Spark """
    type: constr(min_length=1)
    stats_range: constr(min_length=1)  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: NonNegativeInt
    to_ts: NonNegativeInt
    data: List[SparkT]
    database: Optional[str]
