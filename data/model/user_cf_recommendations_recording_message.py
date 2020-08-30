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
