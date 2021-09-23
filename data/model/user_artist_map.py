import pydantic

from typing import Optional


class UserArtistMapRecord(pydantic.BaseModel):
    """ Each individual record for a user's artist map

    Contains the country_code and artist_count
    """
    country: str
    artist_count: int
    listen_count: Optional[int]  # Make field optional to maintain backward compatibility
