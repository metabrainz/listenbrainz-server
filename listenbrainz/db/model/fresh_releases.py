import uuid
from enum import Enum
from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class ReleaseGroupPrimaryType(Enum):
    ALBUM = "Album"
    SINGLE = "Single"
    EP = "EP"
    OTHER = "Other"
    BROADCAST = "Broadcast"


class ReleaseGroupSecondaryType(Enum):
    COMPILATION = "Compilation"
    SOUNDTRACK = "Soundtrack"
    SPOKENWORD = "Spokenword"
    INTERVIEW = "Interview"
    AUDIOBOOK = "Audiobook"
    LIVE = "Live"
    REMIX = "Remix"
    DJMIX = "DJ-mix"
    MIXTAPESTREET = "Mixtape/Street"
    DEMO = "Demo"
    AUDIO = "Audio drama"
    FIELD = "Field recording"


class FreshRelease(BaseModel):
    """This model contains all of the information needed for one fresh release"""

    # The release date for this release
    release_date: date

    # The MBID for this release
    release_mbid: uuid.UUID

    # The name of this release
    release_name: str

    # The artist credit name for this release
    artist_credit_name: str

    # The array of artist MBIDs
    artist_mbids: List[uuid.UUID]

    # The release group for this release
    release_group_mbid: uuid.UUID

    # The release group's primary type
    release_group_primary_type: Optional[ReleaseGroupPrimaryType]

    # The release group's secondary type
    release_group_secondary_type: Optional[ReleaseGroupSecondaryType]

    # The array of tags for this release
    release_tags: List[str]

    # The listen count for this release
    listen_count: int

    # The cover art archive id of the release's front cover art if it has any
    caa_id: Optional[int]

    # The release mbid of the cover art to use for this release. this will be the same
    # as the release mbid if the release has a cover art. if the release doesn't have a
    # cover art but another release in the release group has it, this mbid will point to
    # that release.
    caa_release_mbid: Optional[uuid.UUID]

    def to_dict(self):
        """Convert this model to a dict for easy jsonification"""

        release = self.dict()
        release["release_date"] = release["release_date"].strftime("%Y-%m-%d")
        if release["release_group_primary_type"] is None:
            del release["release_group_primary_type"]
        else:
            release["release_group_primary_type"] = release["release_group_primary_type"].value
        if release["release_group_secondary_type"] is None:
            del release["release_group_secondary_type"]
        else:
            release["release_group_secondary_type"] = release["release_group_secondary_type"].value

        return release
