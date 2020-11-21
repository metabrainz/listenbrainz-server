import uuid
import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class PlaylistRecording(BaseModel):
    """A recording that is part of a playlist"""
    # Internal id of the playlist
    id: int
    # What playlist this recording is a part of
    playlist_id: int
    # The position of this item in the playlist
    position: int
    # The item
    recording_mbid: uuid.UUID
    # Who added this item to the playlist
    added_by: int
    # When the item was added
    created: datetime.datetime


class Playlist(BaseModel):

    # Database fields
    # The internal ID of the playlist row in the database
    id: int
    # The public-facing uuid of the playlist
    mbid: uuid.UUID
    # The listenbrainz user id who created this playlist
    creator_id: int
    # The name of the playlist
    name: str
    # An optional description of the playlist
    description: Optional[str]
    public: bool = True
    # When the playlist was created
    created: datetime.datetime
    # If the playlist was copied from another one, the id of that playlist
    copied_from_id: Optional[int]
    # If the playlist was created by a bot, the user for who this playlist was created
    created_for_id: Optional[int]
    # If the playlist was created by a bot, some freeform data about it
    algorithm_metadata: Optional[Dict]

    # Computed fields
    created_for: Optional[str]
    copied_from: Optional[uuid.UUID]
    creator: str
    recordings: List[PlaylistRecording]


class WritablePlaylist(Playlist):
    id: int = None
    mbid: str = None
    creator: str = None
    recordings: List[PlaylistRecording] = []
    created: datetime.datetime = None
