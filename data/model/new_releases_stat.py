import pydantic
from typing import List

from pydantic import NonNegativeInt


class NewReleasesStat(pydantic.BaseModel):
    type: str
    user_id: NonNegativeInt
    data: List
