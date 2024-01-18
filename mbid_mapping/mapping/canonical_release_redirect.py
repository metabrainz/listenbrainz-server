from mapping.bulk_table import BulkInsertTable


class CanonicalReleaseRedirect(BulkInsertTable):
    """
        This class creates the canonical releases table.
        This maps any given release mbid to the "most canonical" release in that release group,
        along with the release group mbid.

        When reading the `canonical_release` table, the first release
        (ordered by id) for a given release group is the canonical release.

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__("mapping.canonical_release_redirect", select_conn, insert_conn, batch_size, unlogged)

    def get_create_table_columns(self):
        return [("id",                       "SERIAL"),
                ("release_mbid",             "UUID NOT NULL"),
                ("canonical_release_mbid",   "UUID NOT NULL"),
                ("release_group_mbid",       "UUID NOT NULL"),]

    def get_insert_queries(self):
        return ["""
            WITH canonical_release AS (
                SELECT release.gid rel_mbid
                    , rg.gid rg_mbid
                    , cmdr.id
                    , rank() over (partition by rg.id order by cmdr.id)
                FROM musicbrainz.release
                JOIN musicbrainz.release_group rg
                  ON release.release_group = rg.id
                JOIN mapping.canonical_release_tmp cmdr
                  ON cmdr.release = release.id
            ), first_release AS (
              SELECT *
                FROM canonical_release
               WHERE rank = 1
            ), release_rg AS (
              SELECT release.gid release_mbid
                   , rg.gid release_group_mbid
                FROM musicbrainz.release
                JOIN musicbrainz.release_group rg
                  ON release.release_group = rg.id
           )
              SELECT release_rg.release_mbid
                   , first_release.rel_mbid AS canonical_release_mbid
                   , release_rg.release_group_mbid
                FROM release_rg
                JOIN first_release
                  ON first_release.rg_mbid = release_rg.release_group_mbid
        """]

    def get_post_process_queries(self):
        return []

    def get_index_names(self):
        return [("release_mbid_ndx_canonical_release_redirect", "release_mbid", True)]

    def process_row(self, row):
        return [(row["release_mbid"], row["canonical_release_mbid"], row["release_group_mbid"])]
