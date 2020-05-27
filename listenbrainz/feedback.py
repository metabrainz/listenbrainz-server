import uuid

from typing import List
from pydantic import BaseModel, ValidationError, validator


class Feedback(BaseModel):
    """ Represents a feedback object
        Args:
            user_id: the row id of the user in the DB
            recording_msid: the MessyBrainz ID of the recording
            score: The score associated with the recording (+1/-1 for love/hate respectively)
    """

    user_id: int
    recording_msid: str
    score: int

    @validator('score')
    def check_score_is_valid(cls, scr):
        if scr not in [-1, 0, 1]:
            raise ValueError('Score can have a value of 1, 0 or -1.')
        return scr

    @validator('recording_msid')
    def check_recording_msid_is_valid_uuid(cls, rec_msid):
        try:
            rec_msid = uuid.UUID(rec_msid)
            return str(rec_msid)
        except (AttributeError, ValueError):
            raise ValueError('Recording MSID must be a valid UUID.')
