from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from datetime import datetime
from typing import List, Optional


class UserMissingMusicBrainzDataRecord(BaseModel):
    """ Each individual record for a user's missing musicbrainz data.
    """
    artist_msid: constr(min_length=1)
    artist_name: constr(min_length=1)
    listened_at: constr(min_length=1)
    recording_msid: constr(min_length=1)
    release_msid: Optional[str]
    release_name: Optional[str]
    track_name: constr(min_length=1)

    _validate_uuids: classmethod = validator(
        "artist_msid",
        "recording_msid",
        "release_msid",
        allow_reuse=True
    )(check_valid_uuid)


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
