from pydantic import BaseModel


class SoundcloudArtist(BaseModel):
    id: str
    name: str
    data: dict

class SoundcloudTrack(BaseModel):
    id: str
    name: str
    artist: SoundcloudArtist
    data: dict
