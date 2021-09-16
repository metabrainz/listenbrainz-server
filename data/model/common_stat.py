from datetime import datetime
from typing import TypeVar, Generic, Optional, List

from pydantic.generics import GenericModel


StatT = TypeVar('StatT')


class StatRecordList(GenericModel, Generic[StatT]):
    __root__: List[StatT]


class StatRange(GenericModel, Generic[StatT]):
    to_ts: int
    from_ts: int
    count: Optional[int]
    stats_range: str
    data: StatRecordList[StatT]


class StatApi(StatRange[StatT], Generic[StatT]):
    user_id: int
    last_updated: datetime
