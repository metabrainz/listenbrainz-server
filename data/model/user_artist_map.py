import pydantic

from datetime import datetime
from typing import Optional, List


class UserArtistMapRecord(pydantic.BaseModel):
    """ Each individual record for a user's artist map

    Contains the country_code and artist_count
    """
    country: str
    artist_count: int
    listen_count: Optional[int]  # Make field optional to maintain backward compatibility


class UserArtistMapRecordList(pydantic.BaseModel):
    __root__: List[UserArtistMapRecord]
