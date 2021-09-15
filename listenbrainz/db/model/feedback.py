from copy import copy
import uuid

from datetime import datetime, timezone
from pydantic import BaseModel, ValidationError, validator


class Feedback(BaseModel):
    """ Represents a feedback object
        Args:
            user_id: the row id of the user in the DB
            user_name: (Optional) the MusicBrainz ID of the user
            recording_msid: the MessyBrainz ID of the recording
            score: the score associated with the recording (+1/-1 for love/hate respectively)
            created: (Optional)the timestamp when the feedback record was inserted into DB
    """

    user_id: int
    user_name: str = None
    recording_msid: str
    score: int
    created: datetime = None
    track_metadata: dict = None

    def to_api(self) -> dict:
        fb = copy(self)
        fb.user_id = fb.user_name
        if fb.created is not None:
            fb.created = fb.created.timestamp()
        del fb.user_name

        return fb.dict()

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

