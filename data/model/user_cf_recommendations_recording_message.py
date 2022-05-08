from pydantic import BaseModel, validator, NonNegativeInt, constr
from data.model.validators import check_valid_uuid

from datetime import datetime
from typing import List, Optional

from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataRecord


class UserMissingMusicBrainzDataMessage(BaseModel):
    """ Format of missing musicbrainz data messages sent to the ListenBrainz Server """
    type: constr(min_length=1)
    user_id: NonNegativeInt
    missing_musicbrainz_data: List[UserMissingMusicBrainzDataRecord]
    source: constr(min_length=1)


class UserCreateDataframesMessage(BaseModel):
    """ Format of dataframe creation messages sent to the ListenBrainz Server """
    type: constr(min_length=1)
    dataframe_upload_time: constr(min_length=1)
    total_time: constr(min_length=1)
    from_date: constr(min_length=1)
    to_date: constr(min_length=1)


class UserRecommendationsRecord(BaseModel):
    """ Each individual record for a user's recommendations.
    """
    recording_mbid: constr(min_length=1)
    score: float
    latest_listened_at: Optional[str]

    _validate_recording_mbid: classmethod = validator("recording_mbid", allow_reuse=True)(check_valid_uuid)


class UserRecommendationsJson(BaseModel):
    """ Model for the JSON stored in recommendation.cf_recording tables's recording_mbid column
    """
    top_artist: Optional[List[UserRecommendationsRecord]]
    similar_artist: Optional[List[UserRecommendationsRecord]]
    model_id: Optional[str]
    model_url: Optional[str]


class UserRecommendationsData(BaseModel):
    """ Model for table recommendation.cf_recording
    """
    user_id: NonNegativeInt
    created: datetime
    recording_mbid: UserRecommendationsJson


class UserRecommendationsMessage(BaseModel):
    """ Format of recommendations messages sent to the ListenBrainz Server """
    type: constr(min_length=1)
    user_id: NonNegativeInt
    recommendations: UserRecommendationsJson
