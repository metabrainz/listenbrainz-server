from datasethoster import Query
from pydantic import BaseModel

from listenbrainz.labs_api.labs.api.apple import AppleMusicIdFromMBIDOutput
from listenbrainz.labs_api.labs.api.utils import lookup_using_metadata


class AppleMusicIdFromMetadataInput(BaseModel):
    artist_name: str
    release_name: str
    track_name: str


class AppleMusicIdFromMetadataQuery(Query):
    """ Query to lookup Apple Music track ids using artist name, release name and track name. """

    def names(self):
        return "apple-id-from-metadata", "apple music track ID Lookup using metadata"

    def inputs(self):
        return AppleMusicIdFromMetadataInput

    def introduction(self):
        return """Given the name of an artist, the name of a release and the name of a recording (track)
                  this query will attempt to find a suitable match in apple music."""

    def outputs(self):
        return AppleMusicIdFromMBIDOutput

    def fetch(self, params, source, offset=-1, count=-1):
        data = [p.dict() for p in params]
        return lookup_using_metadata(data, "apple_music")