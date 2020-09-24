import pydantic

from datetime import datetime
from typing import List, Optional

from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataRecord

class UserMissingMusicBrainzDataMessage(pydantic.BaseModel):
    """ Format of missing musicbrainz data messages sent to the ListenBrainz Server """
    type: str
    musicbrainz_id: str
    missing_musicbrainz_data: List[UserMissingMusicBrainzDataRecord]
    source: str


class UserCreateDataframesMessage(pydantic.BaseModel):
    """ Format of dataframe creation messages sent to the ListenBrainz Server """
    type: str
    dataframe_upload_time: str
    total_time: str
    from_date: str
    to_date: str


class UserRecommendationsRecord(pydantic.BaseModel):
    """ Each individual record for a user's recommendations.
    """
    recording_mbid: str
    score: float


class UserRecommendationsJson(pydantic.BaseModel):
    """ Model for the JSON stored in recommendation.cf_recording tables's recording_mbid column
    """
    top_artist: Optional[List[UserRecommendationsRecord]]
    similar_artist: Optional[List[UserRecommendationsRecord]]


class UserRecommendationsData(pydantic.BaseModel):
    """ Model for table recommendation.cf_recording
    """
    user_id: int
    created: datetime
    recording_mbid : UserRecommendationsJson


class UserRecommendationsMessage(pydantic.BaseModel):
    """ Format of recommendations messages sent to the ListenBrainz Server """
    type: str
    musicbrainz_id: str
    recommendations: UserRecommendationsJson
