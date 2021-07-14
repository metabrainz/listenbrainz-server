from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict


class SitewideArtistRecord(BaseModel):
    """ Each individual record for sitewide top artists

        Contains the artist name, MessyBrainz ID, MusicBrainz IDs and listen count.
    """
    artist_msid: Optional[str]
    artist_mbids: List[constr(min_length=1)] = []
    listen_count: NonNegativeInt
    artist_name: str
    
    _validate_artist_msid: classmethod = validator("artist_msid", allow_reuse=True)(check_valid_uuid)
    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)


class SitewideArtistStatRange(BaseModel):
    """ Model for storing most listened-to artists on the website for a
        particular time range.
    """
    to_ts: NonNegativeInt
    from_ts: NonNegativeInt
    time_range: str
    artists: List[SitewideArtistRecord]


class SitewideArtistStatJson(BaseModel):
    """ Model for the JSON stored in the statistics.sitewide table's
        artist column.
    """
    to_ts: NonNegativeInt
    from_ts: NonNegativeInt
    time_ranges: List[SitewideArtistStatRange]


class SitewideArtistStat(BaseModel):
    """ Model for stats around a most listened artists on the website
    """
    stats_range: str
    data: Optional[SitewideArtistStatJson]
    last_updated: datetime
