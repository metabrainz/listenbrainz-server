import re

import psycopg2
from unidecode import unidecode

from mapping.utils import create_schema, insert_rows, log
from mapping.formats import create_formats_table
from mapping.bulk_table import BulkInsertTable
import config

TEST_ARTIST_IDS = [1160983, 49627, 65, 21238]  # Gun'n'roses, beyoncé, portishead, Erik Satie


class MBIDMappingReleases(BulkInsertTable):

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.mbid_mapping_releases", mb_conn, lb_conn, batch_size)
        self.release_index = {}
        self.count = 0

    def get_create_table_columns(self):
        """
            Return the PG query to fetch the insert data. This function should return
            a liost of tuples of two strings: [(column name, column type/constraints/defaults)]
        """

        return [("id",           "SERIAL"),
                ("release",      "INTEGER NOT NULL"),
                ("release_mbid", "UUID NOT NULL")]

    def get_insert_queries(self):
        """
        """

        # The 1 in the WHERE clause refers to MB's Various Artists ID of 1 -- all the various artist albums.
        query = """             SELECT r.id AS release
                                     , r.gid AS release_mbid
                                  FROM musicbrainz.release_group rg
                                  JOIN musicbrainz.release r
                                    ON rg.id = r.release_group
                             LEFT JOIN musicbrainz.release_country rc
                                    ON rc.release = r.id
                                  JOIN musicbrainz.medium m
                                    ON m.release = r.id
                             LEFT JOIN musicbrainz.medium_format mf
                                    ON m.format = mf.id
                             LEFT JOIN mapping.format_sort fs
                                    ON mf.id = fs.format
                                  JOIN musicbrainz.artist_credit ac
                                    ON rg.artist_credit = ac.id
                             LEFT JOIN musicbrainz.release_group_primary_type rgpt
                                    ON rg.type = rgpt.id
                             LEFT JOIN musicbrainz.release_group_secondary_type_join rgstj
                                    ON rg.id = rgstj.release_group
                             LEFT JOIN musicbrainz.release_group_secondary_type rgst
                                    ON rgstj.secondary_type = rgst.id
                                 WHERE rg.artist_credit %s 1
                                       %s
                                 ORDER BY rg.type, rgst.id desc, fs.sort NULLS LAST,
                                          to_date(date_year::TEXT || '-' ||
                                                  COALESCE(date_month,12)::TEXT || '-' ||
                                                  COALESCE(date_day,28)::TEXT, 'YYYY-MM-DD'),
                                          country, rg.artist_credit, rg.name, r.id"""

        queries = []
        for op in ['!=', '=']:
            if config.USE_MINIMAL_DATASET:
                log("{self.table_name}: Using a minimal dataset for artist credit pairs: artist_id %s 1" % op)
                queries.append(query % (op, 'AND rg.artist_credit IN (%s)' % ",".join([str(i) for i in TEST_ARTIST_IDS])))
            else:
                log("{self.table_name}: Using a full dataset for artist credit pairs: artsit_id %s 1" % op)
                queries.append(query % (op, ""))

        return queries

    def get_create_index_queries(self):
        """
            Returns a list of of tuples of index names and column defintion strings:
                [("mbid_mapping_ndx_recording_mbid", "recoding_mbid")]
        """
        return [("mbid_mapping_releases_idx_release", "release"),
                ("mbid_mapping_releases_idx_id",      "id")]

    def process_row(self, row):
        """
        """

        if row["release"] in self.release_index:
            return ()

        self.release_index[row["release"]] = 1
        self.count += 1
        return [(self.count, row["release"], row["release_mbid"])]


def create_mbid_mapping_releases():
    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        bt = MBIDMappingReleases(mb_conn)
        bt.run()
