import pydantic.v1 as pydantic
from typing import List

from pydantic.v1 import NonNegativeInt


class NewReleasesStat(pydantic.BaseModel):
    type: str
    year: NonNegativeInt
    user_id: NonNegativeInt
    data: List
