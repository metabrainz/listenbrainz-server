from pydantic import BaseModel, validator, NonNegativeInt, constr
from data.model.validators import check_valid_uuid

from typing import Optional


class ArtistRecord(BaseModel):
    """ Each individual record for top artists

    Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_mbid: Optional[str]
    listen_count: NonNegativeInt
    artist_name: constr(min_length=1)

    _validate_uuids: classmethod = validator("artist_mbid", allow_reuse=True)(check_valid_uuid)
