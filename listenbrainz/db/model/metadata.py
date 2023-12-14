import uuid
from typing import List, Dict, Optional

from pydantic import BaseModel, NonNegativeInt


class RecordingMetadata(BaseModel):
    """Metadata for a recording that is cached in LB to reduce the impact on MB."""

    # The recording that this metadata is about
    recording_mbid: uuid.UUID

    # The mbids of artists of this recording
    artist_mbids: List[uuid.UUID]

    # The release that this metadata is about -- could be None
    release_mbid: Optional[uuid.UUID]

    # Has this entry been marked dirty for imminent re-fetching?
    dirty: bool

    # JSON which contains metadata about the recording
    recording_data: Dict

    # JSON which contains metadata about the artist for this recording
    artist_data: Dict

    # JSON which contains metadata about the tags for this recording and its artist
    tag_data: Dict

    # JSON which contains metadata about the release for this recording
    release_data: Dict


class ReleaseGroupMetadata(BaseModel):
    """Metadata for a release group that is cached in LB to reduce the impact on MB."""

    # The release_group that this metadata is about
    release_group_mbid: uuid.UUID

    # The mbids of artists of this release_group
    artist_mbids: List[uuid.UUID]

    # Has this entry been marked dirty for imminent re-fetching?
    dirty: bool

    # JSON which contains metadata about the artist for this release_group
    artist_data: Dict

    # JSON which contains metadata about the tags for this release_group and its artist
    tag_data: Dict

    # JSON which contains metadata about the release_group
    release_group_data: Dict

    # JSON which contains metadata about the recordings in the canonical release of this release group
    recording_data: Dict


class ArtistMetadata(BaseModel):
    """Metadata for an artist that is cached in LB to reduce the impact on MB."""

    # The mbids of this artist
    artist_mbid: uuid.UUID

    # Has this entry been marked dirty for imminent re-fetching?
    dirty: bool

    # JSON which contains metadata about the artist for this recording
    artist_data: Dict

    # JSON which contains metadata about the tags for this recording and its artist
    tag_data: Dict

    # JSON which contains metadata about the release group of this artist
    release_group_data: List[Dict]
