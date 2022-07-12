import uuid
from enum import Enum
from datetime import datetime
from typing import List

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
    DJMIX= "DJ-mix"
    MIXTAPESTREET = "Mixtape/Street"
    DEMO = "Demo"
    AUDIO = "drama Audio drama"


class UpcomingRelease(BaseModel):
    """This model contains all of the information needed for one upcoming/recent release"""

    # The release date for this release
    date: datetime

    # The MBID for this release
    release_mbid: uuid.UUID

    # The name of this release
    release_name: str

    # The artist credit name for this release
    artist_credit_name: str

    # The array of artist MBIDs
    artist_mbids: List[uuid.UUID]

    # The release group for this release
    release_group: uuid.UUID

    # The release group's primary type
    release_group_primary_type: ReleaseGroupPrimaryType

    # The release group's secondary type
    release_group_secondary_type: ReleaseGroupSecondaryType
