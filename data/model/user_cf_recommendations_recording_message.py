from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from datetime import datetime
from typing import List, Optional

from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataRecord

class UserMissingMusicBrainzDataMessage(BaseModel):
    """ Format of missing musicbrainz data messages sent to the ListenBrainz Server """
    type: str
    musicbrainz_id: str
    missing_musicbrainz_data: List[UserMissingMusicBrainzDataRecord]
    source: str


class UserCreateDataframesMessage(BaseModel):
    """ Format of dataframe creation messages sent to the ListenBrainz Server """
    type: str
    dataframe_upload_time: str
    total_time: str
    from_date: str
    to_date: str


class UserRecommendationsRecord(BaseModel):
    """ Each individual record for a user's recommendations.
    """
    recording_mbid: constr(min_length=1)
    score: float

    _validate_recording_mbid: classmethod = validator("recording_mbid", allow_reuse=True)(check_valid_uuid)


class UserRecommendationsJson(BaseModel):
    """ Model for the JSON stored in recommendation.cf_recording tables's recording_mbid column
    """
    top_artist: Optional[List[UserRecommendationsRecord]]
    similar_artist: Optional[List[UserRecommendationsRecord]]


class UserRecommendationsData(BaseModel):
    """ Model for table recommendation.cf_recording
    """
    user_id: NonNegativeInt
    created: datetime
    recording_mbid: UserRecommendationsJson


class UserRecommendationsMessage(BaseModel):
    """ Format of recommendations messages sent to the ListenBrainz Server """
    type: str
    musicbrainz_id: str
    recommendations: UserRecommendationsJson
