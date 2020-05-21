from typing import List
from pydantic import BaseModel, ValidationError, validator

class Feedback(BaseModel):
    user_id: int
    recording_msid: str
    score: int

    @validator('score')
    def check_score_is_valid(cls, scr):
        if scr not in [-1, 0, 1]:
            raise ValueError('Score can have a value of 1, 0 or -1.')
        return scr