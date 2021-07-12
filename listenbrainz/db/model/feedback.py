import uuid

from datetime import datetime
from pydantic import BaseModel, ValidationError, validator
from listenbrainz.db.model.validators import check_rec_mbid_msid_is_valid_uuid

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

    @validator('score')
    def check_score_is_valid(cls, scr):
        if scr not in [-1, 0, 1]:
            raise ValueError('Score can have a value of 1, 0 or -1.')
        return scr

    _is_recording_msid_valid: classmethod = validator("recording_msid", allow_reuse=True)(check_rec_mbid_msid_is_valid_uuid)
