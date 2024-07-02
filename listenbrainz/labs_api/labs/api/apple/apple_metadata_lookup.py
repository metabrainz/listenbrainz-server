from listenbrainz.labs_api.labs.api.metadata_index.metadata_index_from_metadata_lookup import \
    MetadataIndexFromMetadataQuery
from listenbrainz.labs_api.labs.api.apple import AppleMusicIdFromMBIDOutput


class AppleMusicIdFromMetadataQuery(MetadataIndexFromMetadataQuery):
    """ Query to lookup apple music track ids using artist name, release name and track name. """


    def __init__(self):
        super().__init__("apple_music")

    def names(self):
        return "apple-music-id-from-metadata", "Apple Music Track ID Lookup using metadata"

    def introduction(self):
        return """Given the name of an artist, the name of a release and the name of a recording (track)
                  this query will attempt to find a suitable match in Apple."""

    def outputs(self):
        return AppleMusicIdFromMBIDOutput
