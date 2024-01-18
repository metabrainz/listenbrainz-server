from mapping.utils import log
from mapping.bulk_table import BulkInsertTable
import config

TEST_ARTIST_IDS = [1160983, 49627, 65, 21238]  # Gun'n'roses, beyoncé, portishead, Erik Satie


class CanonicalRelease(BulkInsertTable):
    """
        This class creates the MBID mapping release table.

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__("mapping.canonical_release", select_conn, insert_conn, batch_size, unlogged)
        self.release_index = {}

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
        # The sorting the release group prinary type by id just happens to be a good sort order for primary
        # type. This isn't the case for the secondary type, thus the custom sort order.
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
                             LEFT JOIN mapping.release_group_combined_type_sort rgcts
                                    ON (rgpt.id = rgcts.primary_type OR (rgpt.id IS NULL AND rgcts.primary_type IS NULL))
                                   AND (rgst.id = rgcts.secondary_type OR (rgst.id IS NULL AND rgcts.secondary_type IS NULL))
                                 WHERE rg.artist_credit %s 1
                                       %s
                              ORDER BY rgcts.sort NULLS LAST
                                     , fs.sort NULLS LAST
                                     , to_date(date_year::TEXT || '-' ||
                                               COALESCE(date_month,12)::TEXT || '-' ||
                                               COALESCE(date_day,28)::TEXT, 'YYYY-MM-DD')
                                     , country, rg.artist_credit, rg.name, r.id"""

        queries = []
        for op in ['!=', '=']:
            if config.USE_MINIMAL_DATASET:
                log(f"{self.table_name}: Using a minimal dataset for artist credit pairs: artist_id %s 1" % op)
                queries.append(query % (op, 'AND rg.artist_credit IN (%s)' % ",".join([str(i) for i in TEST_ARTIST_IDS])))
            else:
                log(f"{self.table_name}: Using a full dataset for artist credit pairs: artist_id %s 1" % op)
                queries.append(query % (op, ""))

        return queries

    def get_index_names(self):
        return [("canonical_release_idx_release", "release", False),
                ("canonical_release_idx_id",      "id", False)]

    def process_row(self, row):
        if row["release"] in self.release_index:
            return ()

        self.release_index[row["release"]] = 1
        return [(row["release"], row["release_mbid"])]
