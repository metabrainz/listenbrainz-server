from mapping.bulk_table import BulkInsertTable


class RecordingYear(BulkInsertTable):
    """
        This class is an additional table for CanonicalMusicBrainz metadata in order to
        write a recording_mbid -> year lookup table for use with the mb metadata cache.

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.recording_year", mb_conn, lb_conn, batch_size)

    def get_create_table_columns(self):
        return [("id",                       "SERIAL"),
                ("recording_mbid",           "UUID NOT NULL"),
                ("year",                     "INTEGER NOT NULL")]

    def get_insert_queries(self):
        return []

    def get_post_process_queries(self):
        return ["""
            WITH all_rows AS (
                 SELECT id
                      , row_number() OVER (PARTITION BY recording_mbid ORDER BY id) AS rnum
                   FROM mapping.recording_year_tmp
            )
            DELETE FROM mapping.recording_year_tmp
                  WHERE id IN (SELECT id FROM all_rows WHERE rnum > 1)
        """]

    def get_index_names(self):
        return [("recording_mbid_ndx_recording_year", "recording_mbid", True)]

    def process_row(self, row):
        assert False
