import re
from unidecode import unidecode

from mapping.canonical_musicbrainz_data_base import CanonicalMusicBrainzDataBase


class CanonicalMusicBrainzDataReleaseSupport(CanonicalMusicBrainzDataBase):
    """
        This class creates the MBID mapping tables including the release name in lookups.
    """

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__("mapping.canonical_musicbrainz_data_release_support", select_conn, insert_conn, batch_size, unlogged)

    def get_index_names(self):
        table = "can_mb_data_release"
        return [
            (f"{table}_idx_combined_lookup",              "combined_lookup", False),
            (f"{table}_idx_ac_rec_rel", "artist_credit_name, recording_name, release_name", False),
            (f"{table}_idx_recording_mbid_release_mbid", "recording_mbid, release_mbid", True)
        ]

    def get_post_process_queries(self):
        return ["""
            WITH all_recs AS (
                SELECT id
                     , row_number() OVER (PARTITION BY combined_lookup ORDER BY score) AS rnum
                  FROM mapping.canonical_musicbrainz_data_release_support_tmp
            )   DELETE
                  FROM mapping.canonical_musicbrainz_data_release_support_tmp
                 WHERE id IN (SELECT id FROM all_recs WHERE rnum > 1)
        """]

    def get_combined_lookup(self, row):
        return unidecode(re.sub(r'[^\w]+', '', row['artist_credit_name'] + row['recording_name'] + row['release_name']).lower())
