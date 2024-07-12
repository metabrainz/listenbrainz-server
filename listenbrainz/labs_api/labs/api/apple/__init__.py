from typing import Optional

from listenbrainz.labs_api.labs.api.metadata_index import BaseMetadataIndexOutput


class AppleMusicIdFromMBIDOutput(BaseMetadataIndexOutput):
    apple_music_track_ids: Optional[list[str]]
