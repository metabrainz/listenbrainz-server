from troi.service import Service

from listenbrainz.webserver.views.metadata_api import fetch_metadata


class RecordingLookupService(Service):
    """Replaces the HTTP loopback in RecordingLookupElement.

    Troi checks for this service (slug "recording-lookup") before making
    an HTTP POST to /1/metadata/recording. If registered, this is called
    instead — same data, same dict format, no network round-trip.
    """

    SLUG = "recording-lookup"

    def __init__(self):
        super().__init__(self.SLUG)

    def lookup(self, recording_mbids: list[str], inc: str) -> dict:
        """Return the same dict structure as the /1/metadata/recording endpoint."""
        return fetch_metadata(recording_mbids, inc.split())
