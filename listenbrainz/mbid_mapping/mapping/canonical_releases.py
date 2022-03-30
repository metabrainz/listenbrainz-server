from mapping.bulk_table import BulkInsertTable


class CanonicalReleases(BulkInsertTable):
    """
        This class creates the canonical releases table.

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.recording_canonical_release", mb_conn, lb_conn, batch_size)

    def get_create_table_columns(self):
        return [("id",                       "SERIAL"),
                ("recording_mbid",           "UUID NOT NULL"),
                ("release_mbid",             "UUID NOT NULL")]

    def get_insert_queries(self):
        return []

    def get_post_process_queries(self):
        return ["""INSERT INTO mapping.recording_canonical_release_tmp (recording_mbid, release_mbid)
                        SELECT recording_mbid
                             , canonical_release_mbid AS release_mbid
                          FROM mapping.canonical_recording_tmp""",
                """INSERT INTO mapping.recording_canonical_release_tmp (recording_mbid, release_mbid)
                                 SELECT recording_mbid
                                      , release_mbid
                                   FROM mapping.mbid_mapping_tmp""",
                """COMMIT"""]

    def get_create_index_queries(self):
        return [("recording_mbid_ndx_recording_canonical_release", "recording_mbid", True)]

    def process_row(self, row):
        return []


def create_canonical_releases():
    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        can = CanonicalRecordings(mb_conn)
        can.run()
