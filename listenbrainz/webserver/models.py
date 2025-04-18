from typing import TypedDict, Optional, Any, Dict, List

import pydantic


class SubmitListenUserMetadata(pydantic.BaseModel):
    """ Represents the fields of a user required in submission pipeline"""
    musicbrainz_id: str
    user_id: int


class ArtistActivityArtistEntry(TypedDict):
    name: str
    artist_mbid: Optional[str]
    listen_count: int
    albums: Dict[str, Dict]


class ArtistActivityReleaseGroupData(TypedDict):
    listen_count: int
    release_group_name: str
    release_group_mbid: Optional[str]
    artist_name: Optional[str]
    artists: Optional[List[Dict[str, str]]]
