from pydantic import BaseModel
from typing import List, Optional, Any

class InternetArchiveTrack(BaseModel):
    id: Optional[int] = None  
    track_id: str           
    name: str                 
    artist: List[str]        
    album: Optional[str] = None
    stream_urls: List[str]   
    artwork_url: Optional[str] = None
    data: dict               
    last_updated: Optional[str] = None
