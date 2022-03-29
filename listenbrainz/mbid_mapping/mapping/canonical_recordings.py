from mapping.bulk_table import BulkInsertTable

class CanonicalRecordings(BulkInsertTable):

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.canonical_recording", mb_conn, lb_conn, batch_size)

    def get_create_table_columns(self):
        return [("id",                       "SERIAL"),
                ("recording_mbid",           "UUID NOT NULL"),
                ("canonical_recording_mbid", "UUID NOT NULL"),
                ("canonical_release_mbid",   "UUID NOT NULL")]

    def get_insert_queries(self):
        return []

    def get_post_process_queries(self):
        return ["""
            WITH all_rows AS (
                 SELECT id
                      , row_number() OVER (PARTITION BY recording_mbid ORDER BY id) AS rnum
                   FROM mapping.tmp_canonical_recording
            )
            DELETE FROM mapping.tmp_canonical_recording
                  WHERE id IN (SELECT id FROM all_rows WHERE rnum > 1)
        """]

    def get_create_index_queries(self):
        return [("canonical_recording_ndx_canonical_recording_mbid", "combined_lookup", False),
                ("canonical_recording_ndx_recording_mbid",           "recording_mbid", True)]

    def process_row(self, row):
        assert False
