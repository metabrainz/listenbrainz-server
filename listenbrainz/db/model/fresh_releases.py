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

    def to_dict(self):
        """Convert this model to a dict for easy jsonification"""

        release = dict(self)
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
