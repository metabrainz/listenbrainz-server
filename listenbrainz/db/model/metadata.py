import uuid
from typing import Dict, Bool

from pydantic import BaseModel, NonNegativeInt


class RecordingMetadata(BaseModel):
    """Metadata for a recording that is cached in LB to reduce the impact on MB."""

    # Internal id metadata entry
    id: NonNegativeInt
    # The recording that this metadata is about
    recording_mbid: uuid.UUID
    # Has this entry been marked dirty for immenent re-fetching?
    dirty: Bool
    # The actual dict (JSON) data that contains the metadata
    data: Dict
