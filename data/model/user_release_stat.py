from pydantic import BaseModel, validator, NonNegativeInt, constr
from data.model.validators import check_valid_uuid

from typing import Optional, List


class UserReleaseRecord(BaseModel):
    """ Each individual record for a user's release stats
    """
    artist_mbids: List[constr(min_length=1)] = []
    release_mbid: Optional[str]
    release_name: str
    listen_count: NonNegativeInt
    artist_name: str
    # to add empty fields to stats API response, for compatibility
    artist_msid: Optional[str]
    release_msid: Optional[str]

    _validate_uuids: classmethod = validator("release_mbid", allow_reuse=True)(check_valid_uuid)

    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)
