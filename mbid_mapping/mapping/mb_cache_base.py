from abc import ABC
from datetime import datetime

from typing import List, Set
import uuid

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal

from mapping.utils import insert_rows, log
from mapping.bulk_table import BulkInsertTable
import config


ARTIST_LINK_GIDS = (
    '99429741-f3f6-484b-84f8-23af51991770',  # social network
    'fe33d22f-c3b0-4d68-bd53-a856badf2b15',  # official homepage
    '689870a4-a1e4-4912-b17f-7b2664215698',  # wikidata
    '93883cf6-e818-4938-990e-75863f8db2d3',  # crowdfunding
    '6f77d54e-1d81-4e1a-9ea5-37947577151b',  # patronage
    'e4d73442-3762-45a8-905c-401da65544ed',  # lyrics
    '611b1862-67af-4253-a64f-34adba305d1d',  # purchase for mail-order
    'f8319a2f-f824-4617-81c8-be6560b3b203',  # purchase for download
    '34ae77fe-defb-43ea-95d4-63c7540bac78',  # download for free
    '769085a1-c2f7-4c24-a532-2375a77693bd',  # free streaming
    '63cc5d1f-f096-4c94-a43f-ecb32ea94161',  # streaming
    '6a540e5b-58c6-4192-b6ba-dbc71ec8fcf0'   # youtube
)
ARTIST_LINK_GIDS_SQL = ", ".join([f"'{x}'" for x in ARTIST_LINK_GIDS])

RECORDING_LINK_GIDS = (
    '628a9658-f54c-4142-b0c0-95f031b544da',  # performer
    '59054b12-01ac-43ee-a618-285fd397e461',  # instrument
    '0fdbe3c6-7700-4a31-ae54-b53f06ae1cfa',  # vocal
    '234670ce-5f22-4fd0-921b-ef1662695c5d',  # conductor
    '3b6616c5-88ba-4341-b4ee-81ce1e6d7ebb',  # performing orchestra
    # TODO: the following URL rels are unused (queries only join artist table)
    '92777657-504c-4acb-bd33-51a201bd57e1',  # purchase for download
    '45d0cbc5-d65b-4e77-bdfd-8a75207cb5c5',  # download for free
    '7e41ef12-a124-4324-afdb-fdbae687a89c',  # free streaming
    'b5f3058a-666c-406f-aafb-f9249fc7b122'   # streaming
)
RECORDING_LINK_GIDS_SQL = ", ".join([f"'{x}'" for x in RECORDING_LINK_GIDS])


class MusicBrainzEntityMetadataCache(BulkInsertTable, ABC):
    """
        This class creates the MB metadata cache

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, table, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__(table, select_conn, insert_conn, batch_size, unlogged)
        # cache the last updated to avoid calling it millions of times for the entire cache,
        # not initializing it here because there can be a huge time gap between initialization
        # and the actual query to fetch and insert the items in the cache. the pre_insert_queries_db_setup
        # is called just before the insert queries are run.
        self.last_updated = None

    def get_insert_queries(self):
        return [self.get_metadata_cache_query(with_values=config.USE_MINIMAL_DATASET)]

    def pre_insert_queries_db_setup(self, curs):
        self.config_postgres_join_limit(curs)
        self.last_updated = datetime.now()

    def process_row(self, row):
        return [("false", self.last_updated, *self.create_json_data(row))]

    def create_json_data(self, row):
        """ Convert aggregated row data into json data for storing in the cache table """
        pass

    def process_row_complete(self):
        return []

    def get_metadata_cache_query(self, with_values=False):
        """ Return the query to create the metadata cache """
        pass

    def get_delete_rows_query(self):
        pass

    def delete_rows(self, recording_mbids: List[uuid.UUID]):
        """Delete recording MBIDs from the mb_metadata_cache table

        Args:
            recording_mbids: a list of Recording MBIDs to delete
        """
        query = self.get_delete_rows_query()
        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        with conn.cursor() as curs:
            curs.execute(query, (tuple(recording_mbids),))

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
        """ Query the MB database for all items that have been updated since the last update timestamp """
        pass

    def update_dirty_cache_items(self, recording_mbids: Set[uuid.UUID]):
        """Refresh any dirty items in the mb_metadata_cache table.

        This process first looks for all recording MIBDs which are dirty, gets updated metadata for them, and then
        in batches deletes the dirty rows and inserts the updated ones.
        """
        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            with self.select_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
                self.pre_insert_queries_db_setup(mb_curs)

                log(f"{self.table_name} update: Running looooong query on dirty items")
                query = self.get_metadata_cache_query(with_values=True)
                values = [(mbid,) for mbid in recording_mbids]
                execute_values(mb_curs, query, values, page_size=len(values))

                rows = []
                count = 0
                total_rows = len(recording_mbids)
                for row in mb_curs:
                    count += 1
                    data = self.create_json_data(row)
                    rows.append(("false", self.last_updated, *data))
                    if len(rows) >= self.batch_size:
                        batch_recording_mbids = [row[2] for row in rows]
                        self.delete_rows(batch_recording_mbids)
                        insert_rows(lb_curs, self.table_name, rows)
                        conn.commit()
                        log(f"{self.table_name} update: inserted %d rows. %.1f%%" % (count, 100 * count / total_rows))
                        rows = []

                if rows:
                    batch_recording_mbids = [row[2] for row in rows]
                    self.delete_rows(batch_recording_mbids)
                    insert_rows(lb_curs, self.table_name, rows)
                    conn.commit()

        log(f"{self.table_name} update: inserted %d rows. %.1f%%" % (count, 100 * count / total_rows))
        log(f"{self.table_name} update: Done!")


def select_metadata_cache_timestamp(conn, key):
    """ Retrieve the last time the mb metadata cache update was updated """
    query = SQL("SELECT value FROM background_worker_state WHERE key = {key}")\
        .format(key=Literal(key))
    try:
        with conn.cursor() as curs:
            curs.execute(query)
            row = curs.fetchone()
            if row is None:
                log(f"{key} cache: last update timestamp in missing from background worker state")
                return None
            return datetime.fromisoformat(row[0])
    except psycopg2.errors.UndefinedTable:
        log(f"{key} cache: background_worker_state table is missing, create the table to record update timestamps")
        return None


def update_metadata_cache_timestamp(conn, ts: datetime, key):
    """ Update the timestamp of metadata creation in database. The incremental update process will read this
     timestamp next time it runs and only update cache for rows updated since then in MB database. """
    query = SQL("""
        INSERT INTO background_worker_state (key, value)
             VALUES ({key}, %s)
         ON CONFLICT (key)
           DO UPDATE
                 SET value = EXCLUDED.value
    """) \
        .format(key=Literal(key))
    with conn.cursor() as curs:
        curs.execute(query, (ts.isoformat(),))
    conn.commit()


def create_metadata_cache(cache_cls, cache_key, required_tables, use_lb_conn: bool):
    """
        Main function for creating the entity metadata cache and its related tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """
    psycopg2.extras.register_uuid()

    if use_lb_conn:
        mb_uri = config.MB_DATABASE_MASTER_URI or config.MBID_MAPPING_DATABASE_URI
        unlogged = False
    else:
        mb_uri = config.MBID_MAPPING_DATABASE_URI
        unlogged = True

    success = False
    try:
        with psycopg2.connect(mb_uri) as mb_conn:
            # I think sqlalchemy captures tracebacks and obscures where the real problem is
            try:
                lb_conn = None
                if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
                    lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

                for table_cls in required_tables:
                    table = table_cls(mb_conn, lb_conn, unlogged=unlogged)

                    if not table.table_exists():
                        log(f"{table.table_name} table does not exist, first create the table normally")
                        return

                new_timestamp = datetime.now()
                cache = cache_cls(mb_conn, lb_conn, unlogged=unlogged)
                cache.run()
                success = True
            except Exception:
                log(format_exc())

    except psycopg2.OperationalError:
        if not success:
            raise()

        # Otherwise ignore the connection error, makde a new connection

    # the connection times out after the long process above, so start with a fresh connection
    with psycopg2.connect(mb_uri) as mb_conn:
        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

        update_metadata_cache_timestamp(lb_conn or mb_conn, new_timestamp, cache_key)


def incremental_update_metadata_cache(cache_cls, cache_key, use_lb_conn: bool):
    """ Update the MB metadata cache incrementally """
    psycopg2.extras.register_uuid()

    if use_lb_conn:
        mb_uri = config.MB_DATABASE_MASTER_URI or config.MBID_MAPPING_DATABASE_URI
    else:
        mb_uri = config.MBID_MAPPING_DATABASE_URI

    with psycopg2.connect(mb_uri) as mb_conn:
        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

        cache = cache_cls(mb_conn, lb_conn)
        if not cache.table_exists():
            log(f"{cache.table_name}: table does not exist, first create the table normally")
            return

        log(f"{cache.table_name}: starting incremental update")

        timestamp = select_metadata_cache_timestamp(lb_conn or mb_conn, cache_key)
        log(f"{cache.table_name}: last update timestamp - {timestamp}")
        if not timestamp:
            return

        new_timestamp = datetime.now()
        recording_mbids = cache.query_last_updated_items(timestamp)
        cache.update_dirty_cache_items(recording_mbids)

        if len(recording_mbids) == 0:
            log(f"{cache.table_name}: no recording mbids found to update")
            return

        update_metadata_cache_timestamp(lb_conn or mb_conn, new_timestamp, cache_key)

        log(f"{cache.table_name}: incremental update completed")

