import pydantic
from typing import List


class NewReleasesStat(pydantic.BaseModel):
    type: str
    user_name: str
    data: List