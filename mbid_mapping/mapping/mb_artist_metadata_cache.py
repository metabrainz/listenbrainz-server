from datetime import datetime

from typing import List, Set
import uuid

import psycopg2
from psycopg2.errors import OperationalError
import psycopg2.extras
import ujson
from psycopg2.extras import execute_values

from mapping.mb_metadata_cache import ARTIST_LINK_GIDS_SQL, update_metadata_cache_timestamp, \
    select_metadata_cache_timestamp
from mapping.utils import insert_rows, log
from mapping.bulk_table import BulkInsertTable
import config

MB_ARTIST_METADATA_CACHE_TIMESTAMP_KEY = "mb_artist_metadata_cache_last_update_timestamp"


class MusicBrainzArtistMetadataCache(BulkInsertTable):
    """
        This class creates the MB metadata cache

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.mb_artist_metadata_cache", mb_conn, lb_conn, batch_size)

    def get_create_table_columns(self):
        # this table is created in local development and tables using admin/timescale/create_tables.sql
        # remember to keep both in sync.
        return [("dirty ", "BOOLEAN DEFAULT FALSE"),
                ("artist_mbid ", "UUID NOT NULL"),
                ("artist_data ", "JSONB NOT NULL"),
                ("tag_data ", "JSONB NOT NULL")]

    def get_insert_queries_test_values(self):
        if config.USE_MINIMAL_DATASET:
            return [[(uuid.UUID(u),) for u in ('e97f805a-ab48-4c52-855e-07049142113d',
                                               'e95e5009-99b3-42d2-abdd-477967233b08',
                                               '97e69767-5d34-4c97-b36a-f3b2b1ef9dae')]]
        else:
            return [[]]

    def get_insert_queries(self):
        return [("MB", self.get_metadata_cache_query(with_values=config.USE_MINIMAL_DATASET))]

    def pre_insert_queries_db_setup(self, curs):
        self.config_postgres_join_limit(curs)

    def get_post_process_queries(self):
        return []

    def get_index_names(self):
        return [("mb_artist_metadata_cache_idx_artist_mbid", "artist_mbid", True),
                ("mb_artist_metadata_cache_idx_dirty", "dirty", False)]

    def process_row(self, row):
        return [("false", *self.create_json_data(row))]

    def process_row_complete(self):
        return []

    def create_json_data(self, row):
        """ Format the data returned into sane JSONB blobs for easy consumption. Return
            recording_data, artist_data, tag_data JSON strings as a tuple.
        """
        artist_mbid = row["artist_mbid"]
        artist = {"name": row["artist_name"]}
        if row["begin_date_year"] is not None:
            artist["begin_year"] = row["begin_date_year"]
        if row["end_date_year"] is not None:
            artist["end_year"] = row["end_date_year"]
        if row["artist_type"] is not None:
            artist["type"] = row["artist_type"]
        if row["gender"] is not None:
            artist["gender"] = row["gender"]
        if row["area"] is not None:
            artist["area"] = row["area"]

        if row["artist_links"]:
            filtered = {}
            for name, url in row["artist_links"]:
                if name is None or url is None:
                    continue
                filtered[name] = url

            if filtered:
                artist["rels"] = filtered

        artist_tags = []
        for tag, count, artist_mbid, genre_mbid in row["artist_tags"] or []:
            tag = {"tag": tag, "count": count, "artist_mbid": artist_mbid}
            if genre_mbid is not None:
                tag["genre_mbid"] = genre_mbid
            artist_tags.append(tag)

        return artist_mbid, ujson.dumps(artist), ujson.dumps({"artist": artist_tags})

    def get_metadata_cache_query(self, with_values=False):
        values_cte = ""
        values_join = ""
        if with_values:
            values_cte = "subset (subset_artist_mbid) AS (values %s), "
            values_join = "JOIN subset ON a.gid = subset.subset_artist_mbid"

        query = f"""WITH {values_cte} artist_rels AS (
                            SELECT a.gid AS artist_mbid
                                 , array_agg(distinct(ARRAY[lt.name, url])) AS artist_links
                              FROM musicbrainz.artist a
                              JOIN musicbrainz.l_artist_url lau
                                ON lau.entity0 = a.id
                              JOIN musicbrainz.url u
                                ON lau.entity1 = u.id
                              JOIN musicbrainz.link l
                                ON lau.link = l.id
                              JOIN musicbrainz.link_type lt
                                ON l.link_type = lt.id
                              {values_join}
                             WHERE lt.gid IN ({ARTIST_LINK_GIDS_SQL})
                          GROUP BY a.gid
                   ), artist_tags AS (
                            SELECT a.gid AS artist_mbid
                                 , array_agg(jsonb_build_array(t.name, count, a.gid, g.gid)) AS artist_tags
                              FROM musicbrainz.artist a
                              JOIN musicbrainz.artist_tag at
                                ON at.artist = a.id
                              JOIN musicbrainz.tag t
                                ON at.tag = t.id
                         LEFT JOIN musicbrainz.genre g
                                ON t.name = g.name
                              {values_join}
                             WHERE count > 0
                          GROUP BY a.gid
                   )
                            SELECT a.gid AS artist_mbid
                                 , a.name AS artist_name
                                 , a.begin_date_year
                                 , a.end_date_year
                                 , at.name AS artist_type
                                 , ag.name AS gender
                                 , ar.name AS area
                                 , artist_links
                                 , artist_tags
                              FROM musicbrainz.artist a
                         LEFT JOIN musicbrainz.artist_type at
                                ON a.type = at.id
                         LEFT JOIN musicbrainz.gender ag
                                ON a.gender = ag.id
                         LEFT JOIN musicbrainz.area ar
                                ON a.area = ar.id
                         LEFT JOIN artist_rels arl
                                ON arl.artist_mbid = a.gid
                         LEFT JOIN artist_tags ats
                                ON ats.artist_mbid = a.gid
                              {values_join}
        """
        return query

    def delete_rows(self, artist_mbids: List[uuid.UUID]):
        """Delete recording MBIDs from the mb_artist_metadata_cache table

        Args:
            artist_mbids: a list of Recording MBIDs to delete
        """
        query = f"""
            DELETE FROM {self.table_name}
                  WHERE artist_mbid IN %s
        """
        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        with conn.cursor() as curs:
            curs.execute(query, (tuple(artist_mbids),))

    def config_postgres_join_limit(self, curs):
        """
        Because of the size of query we need to hint to postgres that it should continue to
        reorder JOINs in an optimal order. Without these settings, PG will take minutes to
        execute the metadata cache query for even for 3-4 mbids. With these settings,
        the query planning time increases by few milliseconds but the query running time
        becomes instantaneous.
        """
        curs.execute('SET geqo = off')
        curs.execute('SET geqo_threshold = 20')
        curs.execute('SET from_collapse_limit = 15')
        curs.execute('SET join_collapse_limit = 15')

    def query_last_updated_items(self, timestamp):
        # there queries mirror the structure and logic of the main cache building queries
        # note that the tags queries in any of these omit the count > 0 clause because possible removal
        # of a tag is also a change.
        # the last_updated considered and last_updated ignored columns below together list all the last_updated
        # columns a given CTE touches. any other tables touched by a given CTE do not have a last_updated column.

        # these queries only take updates and deletions into consideration, not deletes. because the deleted data
        # has already been removed from the database. a periodic rebuild of the entire cache removes deleted rows

        # 1. artist_rels, artist_data, artist_tags, artist
        # these CTEs and tables concern artist data and we fetch artist mbids from these. all of the CTEs touch
        # artist table but do not consider its last_updated column because that is done separately at end. further,
        # the queries here have been simplified to not include recording tables as that will be considered by a
        # separate query.
        #
        # |   CTE / table   |       purpose                  |  last_updated considered           | last_updated ignored
        # |   artist_rels   |  artist - url links            |  link relationship related and url | artist
        # |   artist_data   |  life span, area, type, gender |  area                              | artist
        # |   artist_tags   |  artist tags                   |  recording_tag, genre              | artist
        # |   artist        |                                |  artist                            |
        artist_mbids_query = f"""
            SELECT a.gid
              FROM musicbrainz.artist a
              JOIN musicbrainz.l_artist_url lau
                ON lau.entity0 = a.id
              JOIN musicbrainz.url u
                ON lau.entity1 = u.id
              JOIN musicbrainz.link l
                ON lau.link = l.id
              JOIN musicbrainz.link_type lt
                ON l.link_type = lt.id
             WHERE lt.gid IN ({ARTIST_LINK_GIDS_SQL})
                   AND (
                        lau.last_updated > %(timestamp)s
                     OR   u.last_updated > %(timestamp)s
                     OR  lt.last_updated > %(timestamp)s
                   )
        UNION
            SELECT a.gid
              FROM musicbrainz.artist a
              JOIN musicbrainz.area ar
                ON a.area = ar.id
             WHERE ar.last_updated > %(timestamp)s
        UNION
            SELECT a.gid
              FROM musicbrainz.artist a
              JOIN musicbrainz.artist_tag at
                ON at.artist = a.id
              JOIN musicbrainz.tag t
                ON at.tag = t.id
         LEFT JOIN musicbrainz.genre g
                ON t.name = g.name
             WHERE at.last_updated > %(timestamp)s
                OR  g.last_updated > %(timestamp)s
        UNION
            SELECT a.gid
              FROM musicbrainz.artist a
             WHERE a.last_updated > %(timestamp)s       
        """

        try:
            with self.mb_conn.cursor() as curs:
                self.config_postgres_join_limit(curs)
                artist_mbids = set()

                log("mb metadata cache: querying artist mbids to update")
                curs.execute(artist_mbids_query, {"timestamp": timestamp})
                for row in curs.fetchall():
                    artist_mbids.add(row[0])

                return artist_mbids
        except psycopg2.errors.OperationalError as err:
            log("mb metadata cache: cannot query rows for update", err)
            return None

    def update_dirty_cache_items(self, artist_mbids: Set[uuid.UUID]):
        """Refresh any dirty items in the mb_artist_metadata_cache table.

        This process first looks for all recording MIBDs which are dirty, gets updated metadata for them, and then
        in batches deletes the dirty rows and inserts the updated ones.
        """
        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            with self.mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
                self.config_postgres_join_limit(mb_curs)

                log("mb metadata update: Running looooong query on dirty items")
                query = self.get_metadata_cache_query(with_values=True)
                values = [(mbid,) for mbid in artist_mbids]
                execute_values(mb_curs, query, values, page_size=len(values))

                rows = []
                count = 0
                total_rows = len(artist_mbids)
                for row in mb_curs:
                    count += 1
                    data = self.create_json_data(row)
                    rows.append(("false", *data))
                    if len(rows) >= self.batch_size:
                        batch_artist_mbids = [row[1] for row in rows]
                        self.delete_rows(batch_artist_mbids)
                        insert_rows(lb_curs, self.table_name, rows)
                        conn.commit()
                        log("mb metadata update: inserted %d rows. %.1f%%" % (count, 100 * count / total_rows))
                        rows = []

                if rows:
                    batch_artist_mbids = [row[1] for row in rows]
                    self.delete_rows(batch_artist_mbids)
                    insert_rows(lb_curs, self.table_name, rows)
                    conn.commit()

        log("mb metadata update: inserted %d rows. %.1f%%" % (count, 100 * count / total_rows))
        log("mb metadata update: Done!")


def create_mb_artist_metadata_cache(use_lb_conn: bool):
    """
        Main function for creating the MB metadata cache and its related tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """
    psycopg2.extras.register_uuid()

    if use_lb_conn:
        mb_uri = config.MB_DATABASE_STANDBY_URI or config.MBID_MAPPING_DATABASE_URI
    else:
        mb_uri = config.MBID_MAPPING_DATABASE_URI

    with psycopg2.connect(mb_uri) as mb_conn:
        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

        new_timestamp = datetime.now()
        cache = MusicBrainzArtistMetadataCache(mb_conn, lb_conn)
        cache.run()
        update_metadata_cache_timestamp(lb_conn or mb_conn, new_timestamp, MB_ARTIST_METADATA_CACHE_TIMESTAMP_KEY)


def incremental_update_mb_artist_metadata_cache(use_lb_conn: bool):
    """ Update the MB metadata cache incrementally """
    psycopg2.extras.register_uuid()

    if use_lb_conn:
        mb_uri = config.MB_DATABASE_STANDBY_URI or config.MBID_MAPPING_DATABASE_URI
    else:
        mb_uri = config.MBID_MAPPING_DATABASE_URI

    with psycopg2.connect(mb_uri) as mb_conn:
        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

        cache = MusicBrainzArtistMetadataCache(mb_conn, lb_conn)
        if not cache.table_exists():
            log("mb metadata cache: table does not exist, first create the table normally")
            return

        log("mb metadata cache: starting incremental update")

        timestamp = select_metadata_cache_timestamp(lb_conn or mb_conn, MB_ARTIST_METADATA_CACHE_TIMESTAMP_KEY)
        log(f"mb metadata cache: last update timestamp - {timestamp}")
        if not timestamp:
            return

        new_timestamp = datetime.now()
        artist_mbids = cache.query_last_updated_items(timestamp)
        cache.update_dirty_cache_items(artist_mbids)

        if len(artist_mbids) == 0:
            log("mb metadata cache: no recording mbids found to update")
            return

        update_metadata_cache_timestamp(lb_conn or mb_conn, new_timestamp, MB_ARTIST_METADATA_CACHE_TIMESTAMP_KEY)

        log("mb metadata cache: incremental update completed")
