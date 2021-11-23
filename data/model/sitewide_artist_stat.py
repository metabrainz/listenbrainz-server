from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from typing import Optional, List


class SitewideArtistRecord(BaseModel):
    """ Each individual record for sitewide top artists

        Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_mbids: List[constr(min_length=1)] = []
    listen_count: NonNegativeInt
    artist_name: constr(min_length=1)
    # to add an empty field to stats API response, for compatibility
    artist_msid: Optional[str]

    _validate_artist_msid: classmethod = validator("artist_msid", allow_reuse=True)(check_valid_uuid)
    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)
