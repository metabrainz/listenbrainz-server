from pydantic import BaseModel

from listenbrainz.labs_api.labs.api.recording_lookup_base import RecordingLookupBaseQuery


class ArtistCreditRecordingReleaseLookupInput(BaseModel):
    artist_credit_name: str
    recording_name: str
    release_name: str


class ArtistCreditRecordingReleaseLookupQuery(RecordingLookupBaseQuery):

    def get_table_name(self) -> str:
        return "mapping.canonical_musicbrainz_data_release_support"

    def get_lookup_string(self, param) -> str:
        return param.artist_credit_name + param.recording_name + param.release_name

    def names(self):
        return "acrr-lookup", "MusicBrainz Artist Credit Recording Release lookup"

    def inputs(self):
        return ArtistCreditRecordingReleaseLookupInput

    def introduction(self):
        return """
            This lookup performs an semi-exact string match on Artist Credit, Recording and Release. The given
            parameters will have non-word characters removed, unaccented and lower cased before being looked up
            in the database.
        """
