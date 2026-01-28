from listenbrainz.labs_api.labs.api.metadata_index.metadata_index_from_metadata_lookup import \
    MetadataIndexFromMetadataQuery
from listenbrainz.labs_api.labs.api.spotify import SpotifyIdFromMBIDOutput


class SpotifyIdFromMetadataQuery(MetadataIndexFromMetadataQuery):
    """ Query to lookup spotify track ids using artist name, release name and track name. """

    def __init__(self):
        super().__init__("spotify")

    def names(self):
        return "spotify-id-from-metadata", "Spotify Track ID Lookup using metadata"

    def introduction(self):
        return """Given the name of an artist, the name of a release and the name of a recording (track)
                  this query will attempt to find a suitable match in Spotify."""

    def outputs(self):
        return SpotifyIdFromMBIDOutput
