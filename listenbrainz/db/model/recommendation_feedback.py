import uuid

from datetime import datetime
from pydantic import BaseModel, ValidationError, validator


class RecommendationFeedback(BaseModel):
    """ Represents a recommendation feedback object
        Args:
            user_id: the row id of the user in the DB
            user_name: (Optional) the MusicBrainz ID of the user
            recording_mbid: the MusicBrainz ID of the recording
            feedback: the feedback associated with the recording
            created: (Optional)the timestamp when the feedback record was inserted into DB
    """

    user_id: int
    user_name: str = None
    recording_mbid: str
    feedback: str
    created: datetime = None

    @validator('feedback')
    def check_feedback_is_valid(cls, feedback):
        expected_feedback = [
            'like', 'love', 'dislike', 'hate', 'bad_recommendation'
        ]
        if feedback not in expected_feedback:
            raise ValueError('Feedback can only have a value in {}'.format(expected_feedback))
        return feedback

    @validator('recording_mbid')
    def check_recording_mbid_is_valid_uuid(cls, rec_mbid):
        try:
            rec_mbid = uuid.UUID(rec_mbid)
            return str(rec_mbid)
        except (AttributeError, ValueError):
            raise ValueError('Recording MBID must be a valid UUID.')
