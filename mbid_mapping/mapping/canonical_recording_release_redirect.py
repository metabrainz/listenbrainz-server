from mapping.bulk_table import BulkInsertTable


class CanonicalRecordingReleaseRedirect(BulkInsertTable):
    """
        This class creates the canonical recording releases table.
        This maps a recording mbid to the "most canonical" release that the recording appears on.

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.canonical_recording_release_redirect", mb_conn, lb_conn, batch_size)

    def get_create_table_columns(self):
        return [("id",                       "SERIAL"),
                ("recording_mbid",           "UUID NOT NULL"),
                ("release_mbid",             "UUID NOT NULL")]

    def get_insert_queries(self):
        return []

    def get_post_process_queries(self):
        return ["""INSERT INTO mapping.canonical_recording_release_redirect_tmp (recording_mbid, release_mbid)
                        SELECT recording_mbid
                             , canonical_release_mbid AS release_mbid
                          FROM mapping.canonical_recording_redirect_tmp""",
                """INSERT INTO mapping.canonical_recording_release_redirect_tmp (recording_mbid, release_mbid)
                                 SELECT recording_mbid
                                      , release_mbid
                                   FROM mapping.canonical_musicbrainz_data_tmp"""]

    def get_index_names(self):
        return [("recording_mbid_ndx_canonical_recording_release_redirect", "recording_mbid", True)]

    def process_row(self, row):
        return []
