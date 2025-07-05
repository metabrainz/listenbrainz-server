from pydantic import BaseModel, NonNegativeInt, constr
from typing import List


class ArtistEvolutionRecord(BaseModel):
    time_unit: constr(min_length=1)
    artist_mbid: constr(min_length=1)
    artist_name: constr(min_length=1)
    listen_count: NonNegativeInt