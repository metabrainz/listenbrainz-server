from troi import Recording
from troi.plist import plist
from troi.service import Service

import listenbrainz.db.tags as db_tags


class RecordingSearchByTagService(Service):
    """Replaces troi.recording_search_service.RecordingSearchByTagService.

    Calls db.tags.get_and/get_or() directly instead of the HTTP loopback to
    /1/lb-radio/tags. Object construction copied verbatim from the troi original.
    """

    SLUG = "recording-search-by-tag"

    def __init__(self):
        super().__init__(self.SLUG)

    def search(self, tags, operator, pop_begin, pop_end, num_recordings):
        begin = pop_begin / 100.0
        end = pop_end / 100.0

        if operator.upper() == "AND":
            rows = db_tags.get_and(tags, begin, end, num_recordings)
        else:
            rows = db_tags.get_or(tags, begin, end, num_recordings)

        return plist([Recording(mbid=rec["recording_mbid"], musicbrainz={"popularity": rec["percent"]}) for rec in rows])
