import re
from unidecode import unidecode

from mapping.canonical_musicbrainz_data_base import CanonicalMusicBrainzDataBase


class CanonicalMusicBrainzDataRelease(CanonicalMusicBrainzDataBase):
    """
        This class creates the MBID mapping tables including the release name in lookups.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.canonical_musicbrainz_data_release", mb_conn, lb_conn, batch_size)

    def get_index_names(self):
        table = self.table_name.split(".")[-1]
        return [
            (f"{table}_idx_combined_lookup",              "combined_lookup", False),
            (f"{table}_idx_artist_credit_recording_name_release_name", "artist_credit_name, recording_name, release_name", False),
            (f"{table}_idx_recording_mbid_release_mbid", "recording_mbid, release_mbid", True)
        ]

    def get_post_process_queries(self):
        return []

    def get_combined_lookup(self, row):
        return unidecode(re.sub(r'[^\w]+', '', row['artist_credit_name'] + row['recording_name'] + row['release_name']).lower())
