import pydantic

from datetime import datetime
from typing import List, Optional


class UserMissingMusicBrainzDataRecord(pydantic.BaseModel):
    """ Each individual record for a user's missing musicbrainz data.
    """
    artist_name: str
    listened_at: str
    release_name: Optional[str]
    recording_name: str


class UserMissingMusicBrainzDataJson(pydantic.BaseModel):
    """ Model for the JSON stored in the missing_musicbrainz_data table's data column
    """
    missing_musicbrainz_data: Optional[List[UserMissingMusicBrainzDataRecord]]


class UserMissingMusicBrainzData(pydantic.BaseModel):
    """ Model for table 'missing_musicbrainz_data'
    """
    user_id: int
    created: datetime
    data: UserMissingMusicBrainzDataJson
