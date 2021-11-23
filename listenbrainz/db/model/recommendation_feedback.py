from datetime import datetime
from pydantic import BaseModel, NonNegativeInt, validator, constr
from data.model.validators import check_valid_uuid


def get_allowed_ratings():
    """ Get rating values that can be submitted corresponding to a recommendation.
    """
    return ['like', 'love', 'dislike', 'hate', 'bad_recommendation']


class RecommendationFeedbackSubmit(BaseModel):
    """ Represents a recommendation feedback submit object.
        Args:
            user_id: the row id of the user in the DB
            recording_mbid: the MusicBrainz ID of the recording
            rating: the feedback associated with the recommendation.
                    Refer to "recommendation_feedback_type_enum" in admin/sql/create_types.py
                    for allowed rating values.
            created: (Optional)the timestamp when the feedback record was inserted into DB
    """

    user_id: NonNegativeInt
    recording_mbid: constr(min_length=1)
    rating: constr(min_length=1)
    created: datetime = None

    @validator('rating')
    def check_feedback_is_valid(cls, rating):
        expected_rating = get_allowed_ratings()
        if rating not in expected_rating:
            raise ValueError('Feedback can only have a value in {}'.format(expected_rating))
        return rating

    _is_recording_mbid_valid: classmethod = validator("recording_mbid", allow_reuse=True)(check_valid_uuid)


class RecommendationFeedbackDelete(BaseModel):
    """ Represents a recommendation feedback delete object.
        Args:
            user_id: the row id of the user in the DB
            recording_mbid: the MusicBrainz ID of the recommendation
    """

    user_id: NonNegativeInt
    recording_mbid: constr(min_length=1)

    _is_recording_mbid_valid: classmethod = validator("recording_mbid", allow_reuse=True)(check_valid_uuid)
