from datasethoster import Query
from pydantic import BaseModel

from listenbrainz.labs_api.labs.api.spotify import SpotifyIdFromMBIDOutput
from listenbrainz.labs_api.labs.api.spotify.utils import lookup_using_metadata


class SpotifyIdFromMetadataInput(BaseModel):
    artist_name: str
    release_name: str
    track_name: str


class SpotifyIdFromMetadataQuery(Query):
    """ Query to lookup spotify track ids using artist name, release name and track name. """

    def names(self):
        return "spotify-id-from-metadata", "Spotify Track ID Lookup using metadata"

    def inputs(self):
        return SpotifyIdFromMetadataInput

    def introduction(self):
        return """Given the name of an artist, the name of a release and the name of a recording (track)
                  this query will attempt to find a suitable match in Spotify."""

    def outputs(self):
        return SpotifyIdFromMBIDOutput

    def fetch(self, params, offset=-1, count=-1):
        data = [p.dict() for p in params]
        return lookup_using_metadata(data)
