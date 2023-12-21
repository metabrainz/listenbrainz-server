from pydantic import BaseModel, validator, NonNegativeInt, constr
from data.model.validators import check_valid_uuid

from typing import Optional, List, Dict


class ReleaseGroupRecord(BaseModel):
    """ Each individual record for a user's release group stats
    """
    artist_mbids: List[constr(min_length=1)] = []
    release_group_mbid: Optional[str]
    release_group_name: str
    listen_count: NonNegativeInt
    artist_name: str
    caa_id: Optional[NonNegativeInt]
    caa_release_mbid: Optional[str]
    artists: Optional[List[Dict]]

    _validate_uuids: classmethod = validator("release_group_mbid", allow_reuse=True)(check_valid_uuid)
    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)
