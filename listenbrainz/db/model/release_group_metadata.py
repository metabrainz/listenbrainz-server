import uuid
from typing import List, Dict, Optional

from pydantic import BaseModel, NonNegativeInt


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
