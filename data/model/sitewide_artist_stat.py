import pydantic

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict


class SitewideArtistRecord(pydantic.BaseModel):
    """ Each individual record for sitewide top artists

    Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_msid: Optional[str]
    artist_mbids: List[str] = []
    listen_count: int
    artist_name: str


class SitewideArtistStatRange(pydantic.BaseModel):
    """ Model for most listened-to artists on the website for a particular
    time range. Currently supports week, month, year and all-time
    """
    to_ts: int
    from_ts: int
    artists: Dict[str, List[SitewideArtistRecord]]


class SitewideArtistStat(pydantic.BaseModel):
    """ Model for stats around a most listened artists on the website
    """
    stats_range: str
    data: Optional[SitewideArtistStatRange]
    last_updated: datetime
