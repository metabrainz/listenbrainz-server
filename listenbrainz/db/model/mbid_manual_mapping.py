import datetime
from typing import Optional
import uuid

from pydantic import BaseModel

class MbidManualMapping(BaseModel):
    """An instance of a msid-mbid mapping manually created by a user"""
    recording_msid: str
    recording_mbid: str
    user_id: int
    created: Optional[datetime.datetime]

    def to_api(self) -> dict:
        return {
            "recording_msid": self.recording_msid,
            "recording_mbid": self.recording_mbid,
            "user_id": self.user_id,
            "created": self.created
        }
