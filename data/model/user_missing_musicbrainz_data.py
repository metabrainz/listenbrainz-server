from pydantic import BaseModel, NonNegativeInt, constr

from datetime import datetime
from typing import List, Optional


class UserMissingMusicBrainzDataRecord(BaseModel):
    """ Each individual record for a user's missing musicbrainz data.
    """
    artist_name: constr(min_length=1)
    listened_at: constr(min_length=1)
    release_name: Optional[str]
    recording_name: constr(min_length=1)
    recording_msid: constr(min_length=1)


class UserMissingMusicBrainzDataJson(BaseModel):
    """ Model for the JSON stored in the missing_musicbrainz_data table's data column
    """
    missing_musicbrainz_data: Optional[List[UserMissingMusicBrainzDataRecord]]


class UserMissingMusicBrainzData(BaseModel):
    """ Model for table 'missing_musicbrainz_data'
    """
    user_id: NonNegativeInt
    created: datetime
    data: UserMissingMusicBrainzDataJson
