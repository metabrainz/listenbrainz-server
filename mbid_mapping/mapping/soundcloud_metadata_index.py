import re

import psycopg2
from unidecode import unidecode

import config
from mapping.bulk_table import BulkInsertTable
from mapping.utils import log


class SoundCloudMetadataIndex(BulkInsertTable):
    """
        This class creates the metadata index for external music services, that support albums,
        using the reverse painters' algorithm.
    """

    def get_post_process_queries(self):
        return []

    def process_row_complete(self):
        pass

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__("mapping.soundcloud_metadata_index", select_conn, insert_conn, batch_size, unlogged)
        self.row_id = 0

    def get_create_table_columns(self):
        return [("id",                               "SERIAL"),
                ("artist_id",                        "TEXT NOT NULL"),
                ("track_id",                         "TEXT NOT NULL"),
                ("combined_lookup_without_album",    "TEXT NOT NULL"),
                ("score",                            "INTEGER NOT NULL")]

    def get_insert_queries(self):
        """ Retrieve the album name, track name, artist name for all tracks in spotify cache in a specific order.
        These name fields will be used to calculate a lookup for each track which will then be used for matching
        purposes. The order by determines the tie-breaking score in case of multiple rows have the same lookup.
        """
        return [f"""
            SELECT t.track_id AS track_id
                 , t.name AS track_name
                 , t.artist_id AS artist_id
                 , a.name AS artist_name
              FROM soundcloud_cache.track t
              JOIN soundcloud_cache.artist a
                ON t.artist_id = a.artist_id
          GROUP BY t.track_id
                 , t.name
                 , t.artist_id
                 , a.name
                 , t.release_year
                 , t.release_month
                 , t.release_day
          ORDER BY t.release_year NULLS LAST
                 , t.release_month NULLS LAST
                 , t.release_day NULLS LAST
                 , track_id
                 , track_name
                 , artist_name
        """]

    def get_index_names(self):
        return [("soundcloud_metadata_index_idx_combined_lookup", "combined_lookup_without_album", False)]

    def process_row(self, row):
        """ Calculate lookup for each track and assign a score based on ordering """
        combined_lookup = unidecode(re.sub(r"[^\w]+", "", row["artist_name"] + row["track_name"]).lower())
        return {"mapping.soundcloud_metadata_index": [
            (
                row["artist_id"],
                row["track_id"],
                combined_lookup,
                -self.row_id
            )
        ]}


def create_soundcloud_metadata_index(use_lb_conn: bool):
    """
        Main function for creating the soundcloud metadata index

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """

    lb_conn = None
    if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
        lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)
    log("soundcloud_metadata_index: start!")

    ndx = SoundCloudMetadataIndex(lb_conn)
    ndx.run()

    log("soundcloud_metadata_index: done!")
