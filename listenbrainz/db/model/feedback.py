from copy import copy

from datetime import datetime
from pydantic import NonNegativeInt, validator
from listenbrainz.db.msid_mbid_mapping import MsidMbidModel


class Feedback(MsidMbidModel):
    """ Represents a feedback object
        Args:
            user_id: the row id of the user in the DB
            user_name: (Optional) the MusicBrainz ID of the user
            recording_msid: the MessyBrainz ID of the recording
            score: the score associated with the recording (+1/-1 for love/hate respectively)
            created: (Optional)the timestamp when the feedback record was inserted into DB
    """

    user_id: NonNegativeInt
    user_name: str = None
    score: int
    created: datetime = None

    def to_api(self) -> dict:
        data = self.dict()
        data["user_id"] = self.user_name
        if self.created is not None:
            data["created"] = int(self.created.timestamp())
        data.pop("user_name", None)
        return data


    @validator('score')
    def check_score_is_valid(cls, scr):
        if scr not in [-1, 0, 1]:
            raise ValueError('Score can have a value of 1, 0 or -1.')
        return scr
