from pydantic import BaseModel
from typing import Optional

class InternetArchiveTrack(BaseModel):
    id: str
    track_id: Optional[str] = None  # unique identifier for the track
    title: str
    creator: str
    artist: Optional[str] = None    # optional field to store artist name if different from creator
    album: str = ""
    year: str = ""
    notes: str = ""
    topics: str = "" 
    stream_url: str
    duration: Optional[int] = None
    artwork_url: Optional[str] = None
    date: Optional[str] = None
