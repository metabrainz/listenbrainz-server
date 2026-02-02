from listenbrainz.labs_api.labs.api.metadata_index.metadata_index_from_mbid_lookup import MetadataIndexFromMBIDQuery
from listenbrainz.labs_api.labs.api.soundcloud import SoundCloudIdFromMBIDOutput


class SoundCloudIdFromMBIDQuery(MetadataIndexFromMBIDQuery):
    """ Query to lookup soundcloud track ids using recording mbids. """

    def __init__(self):
        super().__init__("soundcloud")

    def names(self):
        return "soundcloud-id-from-mbid", "SoundCloud Track ID Lookup using recording mbid"

    def introduction(self):
        return """Given a recording mbid, lookup its metadata using canonical metadata
        tables and using that attempt to find a suitable match in SoundCloud."""

    def outputs(self):
        return SoundCloudIdFromMBIDOutput
