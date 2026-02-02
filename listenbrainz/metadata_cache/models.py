import enum
from typing import Optional

from pydantic import BaseModel


class Artist(BaseModel):
    id: str
    name: str
    data: dict


class Track(BaseModel):
    id: str
    name: str
    track_number: int
    artists: list[Artist]
    data: dict


class AlbumType(enum.Enum):
    album = 'album'
    single = 'single'
    compilation = 'compilation'


class Album(BaseModel):
    id: str
    name: str
    type_: AlbumType
    release_date: Optional[str]
    tracks: list[Track]
    artists: list[Artist]
    data: dict
