from pydantic import BaseModel, NonNegativeInt, constr

from typing import Optional


class UserArtistMapRecord(BaseModel):
    """ Each individual record for a user's artist map

    Contains the country_code and artist_count
    """
    country: constr(min_length=1)
    artist_count: NonNegativeInt
    listen_count: Optional[NonNegativeInt]  # Make field optional to maintain backward compatibility
