from datetime import datetime
from typing import TypeVar, Generic, Optional

from pydantic.generics import GenericModel


StatT = TypeVar('StatT')


class StatRange(GenericModel, Generic[StatT]):
    to_ts: int
    from_ts: int
    count: Optional[int]
    stats_range: str
    data: StatT


class StatApi(StatRange[StatT], Generic[StatT]):
    user_id: int
    last_updated: datetime
