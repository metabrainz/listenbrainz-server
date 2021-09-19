import pydantic

from typing import Optional, List


class UserArtistRecord(pydantic.BaseModel):
    """ Each individual record for top artists

    Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_mbids: List[str] = []
    listen_count: int
    artist_name: str
    # to add an empty field to stats API response, for compatibility
    artist_msid: Optional[str]
