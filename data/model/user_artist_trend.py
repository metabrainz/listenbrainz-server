from pydantic import BaseModel
from typing import List


class ArtistTrendEntry(BaseModel):
    date: str
    artist_name: str
    listen_count: int


class ArtistTrendRecord(BaseModel):
    __root__: List[ArtistTrendEntry]
