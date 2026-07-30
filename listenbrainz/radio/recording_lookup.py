from troi.service import Service

from listenbrainz.db.metadata import get_metadata_for_recording
from listenbrainz.webserver import ts_conn


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
        incs = inc.split()
        entries = get_metadata_for_recording(ts_conn, recording_mbids)

        result = {}
        for entry in entries:
            data = {"recording": entry.recording_data}
            if "artist" in incs:
                data["artist"] = entry.artist_data
            if "tag" in incs:
                data["tag"] = entry.tag_data
            if "release" in incs:
                data["release"] = entry.release_data
            result[str(entry.recording_mbid)] = data

        return result
