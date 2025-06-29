from pydantic import BaseModel, NonNegativeInt, constr
from typing import List


class ArtistEvolutionEntry(BaseModel):
    date: constr(min_length=1)
    artist_name: constr(min_length=1)
    listen_count: NonNegativeInt


class ArtistEvolutionRecord(BaseModel):
    __root__: List[ArtistEvolutionEntry]
