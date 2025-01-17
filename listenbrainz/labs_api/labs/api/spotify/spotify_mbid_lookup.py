from listenbrainz.labs_api.labs.api.metadata_index.metadata_index_from_mbid_lookup import MetadataIndexFromMBIDQuery
from listenbrainz.labs_api.labs.api.spotify import SpotifyIdFromMBIDOutput


class SpotifyIdFromMBIDQuery(MetadataIndexFromMBIDQuery):
    """ Query to lookup spotify track ids using recording mbids. """

    def __init__(self):
        super().__init__("spotify")

    def names(self):
        return "spotify-id-from-mbid", "Spotify Track ID Lookup using recording mbid"

    def introduction(self):
        return """Given a recording mbid, lookup its metadata using canonical metadata
        tables and using that attempt to find a suitable match in Spotify."""

    def outputs(self):
        return SpotifyIdFromMBIDOutput
