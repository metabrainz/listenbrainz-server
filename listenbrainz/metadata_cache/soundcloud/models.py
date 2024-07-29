from typing import Optional

from pydantic import BaseModel


class SoundcloudArtist(BaseModel):
    id: str
    name: str
    data: dict

class SoundcloudTrack(BaseModel):
    id: str
    name: str
    release_year: Optional[int]
    release_month: Optional[int]
    release_day: Optional[int]
    artist: SoundcloudArtist
    data: dict
