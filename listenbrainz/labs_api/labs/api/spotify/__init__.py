from typing import Optional

from listenbrainz.labs_api.labs.api.metadata_index import BaseMetadataIndexOutput


class SpotifyIdFromMBIDOutput(BaseMetadataIndexOutput):
    spotify_track_ids: Optional[list[str]]
