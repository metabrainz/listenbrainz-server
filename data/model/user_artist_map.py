from pydantic import BaseModel, NonNegativeInt, constr

from typing import Optional, List


class UserArtistMapArtist(BaseModel):
    """ Each individual artist inside a country of the artist map """
    artist_name: constr(min_length=1)
    artist_mbid: constr(min_length=1)
    listen_count: NonNegativeInt


class UserArtistMapRecord(BaseModel):
    """ Each individual record for a user's artist map

    Contains the country_code and artist_count
    """
    country: constr(min_length=1)
    artist_count: NonNegativeInt
    listen_count: NonNegativeInt  # listen count of all artists in a country
    artists: Optional[List[UserArtistMapArtist]]
