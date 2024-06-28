import uuid
from typing import Optional

from pydantic import BaseModel


class AppleMusicIdFromMBIDOutput(BaseModel):
    recording_mbid: Optional[uuid.UUID]
    artist_name: Optional[str]
    release_name: Optional[str]
    track_name: Optional[str]
    apple_track_ids: Optional[list[str]]