import pydantic

from typing import Optional, List


class UserReleaseRecord(pydantic.BaseModel):
    """ Each individual record for a user's release stats
    """
    artist_mbids: List[str] = []
    release_mbid: Optional[str]
    release_name: str
    listen_count: int
    artist_name: str
    # to add empty fields to stats API response, for compatibility
    artist_msid: Optional[str]
    release_msid: Optional[str]
