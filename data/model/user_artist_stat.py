from pydantic import BaseModel, validator, NonNegativeInt, constr
from data.model.validators import check_valid_uuid

from typing import Optional, List


class ArtistRecord(BaseModel):
    """ Each individual record for top artists

    Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_mbids: List[constr(min_length=1)] = []
    listen_count: NonNegativeInt
    artist_name: constr(min_length=1)

    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)
