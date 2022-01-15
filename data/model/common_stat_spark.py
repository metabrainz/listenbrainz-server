# This file contains models for spark -> db statistics.
from typing import TypeVar, Generic, List

from pydantic import constr, NonNegativeInt, BaseModel
from pydantic.generics import GenericModel


SparkT = TypeVar("SparkT")

class MultipleUserStatRecords(GenericModel, Generic[SparkT]):
    musicbrainz_id: constr(min_length=1)
    count: NonNegativeInt
    data: List[SparkT]


class StatMessage(GenericModel, Generic[SparkT]):
    """ Format of messages sent to the ListenBrainz Server from Spark """
    type: constr(min_length=1)
    stats_range: constr(min_length=1)  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: NonNegativeInt
    to_ts: NonNegativeInt
    data: List[SparkT]
