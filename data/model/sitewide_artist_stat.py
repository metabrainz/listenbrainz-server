import pydantic

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict


class SitewideArtistRecord(pydantic.BaseModel):
    """ Each individual record for sitewide top artists

        Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_mbids: List[str] = []
    listen_count: int
    artist_name: str
    # to add an empty field to stats API response, for compatibility
    artist_msid: Optional[str]
