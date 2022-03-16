import uuid
from typing import List, Dict

from pydantic import BaseModel, NonNegativeInt


class RecordingMetadata(BaseModel):
    """Metadata for a recording that is cached in LB to reduce the impact on MB."""

    # Internal id metadata entry
    id: NonNegativeInt
    # The recording that this metadata is about
    recording_mbid: uuid.UUID
    # Has this entry been marked dirty for immenent re-fetching?
    dirty: bool
    # JSON which contains metadata about the recording
    recording_data: Dict
    # JSON which contains metadata about the artist for this recording
    artist_data: List[Dict]
    # JSON which contains metadata about the tags for this recording and its artist
    tag_data: Dict
