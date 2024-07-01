from listenbrainz.labs_api.labs.api.metadata_index.metadata_index_from_mbid_lookup import MetadataIndexFromMBIDQuery
from listenbrainz.labs_api.labs.api.apple import AppleMusicIdFromMBIDOutput


class AppleMusicIdFromMBIDQuery(MetadataIndexFromMBIDQuery):
    """ Query to lookup apple music track ids using recording mbids. """

    def __init__(self):
        super().__init__("apple_music")

    def names(self):
        return "apple-music-id-from-mbid", "Apple Music Track ID Lookup using recording mbid"

    def introduction(self):
        return """Given a recording mbid, lookup its metadata using canonical metadata
        tables and using that attempt to find a suitable match in Apple."""

    def outputs(self):
        return AppleMusicIdFromMBIDOutput
