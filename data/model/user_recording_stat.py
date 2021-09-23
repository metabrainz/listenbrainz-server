import pydantic

from typing import Optional, List


class UserRecordingRecord(pydantic.BaseModel):
    """ Each individual record for a user's recording stats
    """
    artist_name: str
    artist_mbids: List[str] = []
    recording_mbid: Optional[str]
    release_name: Optional[str]
    release_mbid: Optional[str]
    track_name: str
    listen_count: int
    # to add empty fields to stats API response, for compatibility
    artist_msid: Optional[str]
    recording_msid: Optional[str]
    release_msid: Optional[str]
