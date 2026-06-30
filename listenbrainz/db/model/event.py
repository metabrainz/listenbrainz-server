import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel


class EventMetadata(BaseModel):
    """
    Metadata for an event in LB.
    """

    # The event that this metadata is about
    event_mbid: uuid.UUID

    # MusicBrainz's internal event id, which mb_event_artist_cache rows join on
    event_id: int

    # The name of the event
    event_name: str

    # The date the event starts on; MB allows any part of a date to be missing
    begin_date_year: Optional[int]
    begin_date_month: Optional[int]
    begin_date_day: Optional[int]

    # The date the event ends on; MB allows any part of a date to be missing
    end_date_year: Optional[int]
    end_date_month: Optional[int]
    end_date_day: Optional[int]

    # The begin date combined with the event's start time, None unless both are complete. MB gives the local
    # time at the venue with no timezone, and the cache stores it as UTC, so to_api() drops the offset
    event_time: Optional[datetime]

    # Whether the event was cancelled
    cancelled: bool

    # Set by MB as soon as an end date is entered, so it does not mean the date has passed
    ended: bool

    # The type of the event, for example Concert or Festival; could be None
    event_type_gid: Optional[uuid.UUID]

    # MB's event_art_presence enum as text: absent, present or darkened
    event_art_presence: str

    # The first place linked to the event (MB does not mark one as primary); could be None
    place_mbid: Optional[uuid.UUID]

    # The name of that place; could be None
    place_name: Optional[str]

    # The area of that place, or the event's own area link when it has no place; could be None
    area_mbid: Optional[uuid.UUID]

    # The community rating of the event; could be None
    rating: Optional[int]

    # How many ratings the community rating is based on; could be None
    rating_count: Optional[int]

    # JSON which contains the optional parts of the event: type, disambiguation, setlist,
    # area_name, rels, parts, part_of, series, tags and event_art_id
    event_data: Dict

    def to_api(self) -> dict:
        """
        Returns an API serialisable dict.
        API layer handles event data unpacking based on which inc options were requested.
        """
        result = {
            "event_mbid": str(self.event_mbid),
            "event_name": self.event_name,
            "begin_date_year": self.begin_date_year,
            "begin_date_month": self.begin_date_month,
            "begin_date_day": self.begin_date_day,
            "end_date_year": self.end_date_year,
            "end_date_month": self.end_date_month,
            "end_date_day": self.end_date_day,
            "event_time": self.event_time.astimezone(timezone.utc).replace(tzinfo=None).isoformat() if self.event_time else None,
            "cancelled": self.cancelled,
            "ended": self.ended,
            "event_art_presence": self.event_art_presence,
            "rating": self.rating,
            "rating_count": self.rating_count,
        }
        if self.event_type_gid:
            result["event_type_gid"] = str(self.event_type_gid)
        if self.place_mbid:
            result["place_mbid"] = str(self.place_mbid)
            result["place_name"] = self.place_name
        if self.area_mbid:
            result["area_mbid"] = str(self.area_mbid)
        return result
