from pydantic import BaseModel

class InternetArchiveTrack(BaseModel):
    id: str
    title: str
    creator: str
    album: str = ""
    year: str = ""
    notes: str = ""
    topics: str = "" 
    stream_url: str
    duration: int | None = None
    artwork_url: str | None = None
    date: str | None = None
