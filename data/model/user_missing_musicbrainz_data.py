import pydantic

from datetime import datetime
from typing import List, Optional


class UserMissingMusicBrainzDataRecord(pydantic.BaseModel):
    """ Each individual record for a user's missing musicbrainz data.
    """
    artist_msid: str
    artist_name: str
    listened_at: str
    recording_msid: str
    release_msid: str
    release_name: str
    track_name: str


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
