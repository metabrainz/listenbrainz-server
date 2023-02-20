#!/usr/bin/env python3

from listenbrainz.labs_api.labs.api.recording_lookup_base import RecordingLookupBaseQuery


class ArtistCreditRecordingReleaseLookupQuery(RecordingLookupBaseQuery):

    def get_table_name(self) -> str:
        return "mapping.canonical_musicbrainz_data_release_support"

    def get_lookup_string(self, param) -> str:
        return param["[artist_credit_name]"] + param["[recording_name]"] + param["[release_name]"]

    def names(self):
        return "acr-lookup", "MusicBrainz Artist Credit Recording Release lookup"

    def inputs(self):
        return ['[artist_credit_name]', '[recording_name]', '[release_name]']

    def introduction(self):
        return """
            This lookup performs an semi-exact string match on Artist Credit, Recording and Release. The given
            parameters will have non-word characters removed, unaccented and lower cased before being looked up
            in the database.
        """
