from typing import Optional, List
import pydantic


class AdditionalInfo(pydantic.BaseModel):
  artist_mbids: Optional[List[str]]
  artist_msid: str
  discnumber: Optional[int]
  duration_ms: Optional[int]
  isrc: Optional[str]
  listening_from: Optional[str]
  recording_mbid: Optional[str]
  recording_msid: Optional[str]
  release_artist_name: Optional[str]
  release_artist_names: Optional[List[str]]
  release_group_mbid: Optional[str]
  release_mbid: Optional[str]
  release_msid: Optional[str]
  spotify_album_artist_ids: Optional[List[str]]
  spotify_album_id: Optional[str]
  spotify_artist_ids: Optional[List[str]]
  spotify_id: Optional[str]
  youtube_id: Optional[str]
  origin_url: Optional[str]
  tags: Optional[List[str]]
  track_mbid: Optional[str]
  tracknumber: Optional[int]
  work_mbids: Optional[List[str]]


class TrackMetadata(pydantic.BaseModel):
    artist_name: str
    track_name: str
    release_name: Optional[str]
    additional_info: Optional[AdditionalInfo]


# this is not an exhaustive definition
# it might need updating, please do not rely on it for validation.
class APIListen(pydantic.BaseModel):
    listened_at: int
    user_name: Optional[str]
    inserted_at: Optional[int]
    listened_at_iso: Optional[str]
    playing_now: Optional[bool]
    track_metadata: TrackMetadata
