import abc
import time
from abc import ABC
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from urllib.error import HTTPError

from flask import current_app
from more_itertools import chunked
from psycopg2.extras import execute_values
from psycopg2.sql import Identifier, SQL, Literal, Composable
from sentry_sdk import start_transaction

from listenbrainz.db import couchdb, timescale
import listenbrainz.db.stats as db_stats


class SparkDataset(ABC):
    """ A base class to make it easy to consume bulk datasets that follow the guidelines outlined below.

    Various spark datasets are too big to fit in one message. To allow for pre-processing and post-processing
    of the dataset and to demarcate it from the rest of the messages, we define some common guidelines.

    1. Spark Request Consumer sends a start message when it starts generating data. The handle_start method is called
        on the receipt of this message to allow for pre-processsing, setting up tables etc.
    2. Spark Request Consumer sends multiple messages that contain the actual data of the dataset. The handle_insert
        method is called for each data message.
    3. Spark Request Consumer sends an end message when all the generated data has been sent. The handle_end method
        is called for the end message. Do post-processing here and no more data messages can arrive after this message.
    """

    def __init__(self, name):
        self.name = name

    @abc.abstractmethod
    def handle_start(self, message):
        """ Handler invoked by spark reader when the start message for this dataset arrives """
        pass

    @abc.abstractmethod
    def handle_insert(self, message):
        """ Handler invoked by spark reader when the data messages for this dataset arrives """
        pass

    @abc.abstractmethod
    def handle_end(self, message):
        """ Handler invoked by spark reader when the end message for this dataset arrives """
        pass

    def get_handlers(self):
        """ Various handlers registered with the spark reader for processing of this dataset's messages """
        return {
            f"{self.name}_start": self.handle_start,
            self.name: self.handle_insert,
            f"{self.name}_end": self.handle_end
        }

    def handle_shutdown(self):
        """ Shutdown method invoked when spark reader is stopping """
        pass


class _CouchDbDataset(SparkDataset):
    """ Base class for bulk datasets stored in couchdb. """

    def __init__(self):
        super().__init__(name="couchdb_data")

    def handle_start(self, message):
        """ CouchDB dataset start messages contain a database field, the name of which is used to create a new
         database. """
        match = couchdb.DATABASE_NAME_PATTERN.match(message["database"])
        if not match:
            return
        try:
            couchdb.create_database(match[1] + "_" + match[2] + "_" + match[3])
        except HTTPError as e:
            current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)

    def handle_insert(self, message):
        """ Handling of inserting data in couchdb databases is very varied for each case so its handled separately. """
        raise NotImplementedError()

    def handle_end(self, message):
        """ Delete outdated databases of the same type. """
        # database names are of the format, prefix_YYYYMMDD. calculate and pass the prefix to the
        # method to delete all database of the type except the latest one.
        match = couchdb.DATABASE_NAME_PATTERN.match(message["database"])
        # if the database name does not match pattern, abort to avoid deleting any data inadvertently
        if not match:
            return
        try:
            _, retained = couchdb.delete_database(match[1] + "_" + match[2])
            if retained:
                current_app.logger.info(f"Databases: {retained} matched but weren't deleted because"
                                        f" _LOCK file existed")
        except HTTPError as e:
            current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


CouchDbDataset = _CouchDbDataset()


class _StatsDataset(SparkDataset):

    def __init__(self, stats_type):
        super().__init__(stats_type)
        # doing empirical testing for various numbers of workers, no speedup
        # was observed by raising workers to more than 2 because the bottleneck
        # shifted to stats generation in spark
        self.workers = 2
        self.executor = ThreadPoolExecutor(max_workers=self.workers)

    @abc.abstractmethod
    def get_key(self, message):
        pass

    def insert_stats(self, database, stats_range, from_ts, to_ts, data, key):
        with start_transaction(op="insert", name=f"insert {self.name} - {stats_range} stats"):
            db_stats.insert(
                database,
                from_ts,
                to_ts,
                data,
                key
            )

    def handle_insert(self, message):
        if "database_prefix" in message:
            database = couchdb.list_databases(message["database_prefix"])[0]
        else:
            database = message["database"]
        stats_range = message["stats_range"]
        from_ts = message["from_ts"]
        to_ts = message["to_ts"]

        key = self.get_key(message)

        futures = []
        chunk_size = len(message["data"]) // self.workers
        for chunk in chunked(message["data"], chunk_size):
            f = self.executor.submit(self.insert_stats, database, stats_range, from_ts, to_ts, chunk, key)
            futures.append(f)

        for f in as_completed(futures):
            try:
                f.result()
            except Exception:
                current_app.logger.error(f"Error in writing {self.name} stats: %s", exc_info=True)

    def handle_start(self, message):
        raise NotImplementedError()

    def handle_end(self, message):
        raise NotImplementedError()

    def handle_shutdown(self):
        self.executor.shutdown()


class _UserStatsDataset(_StatsDataset):

    def get_key(self, message):
        return "user_id"

UserEntityStatsDataset = _UserStatsDataset("user_entity")
DailyActivityStatsDataset = _UserStatsDataset("user_daily_activity")
ListeningActivityStatsDataset = _UserStatsDataset("user_listening_activity")


class _EntityListenerStatsDataset(_StatsDataset):

    def __init__(self):
        super().__init__("entity_listener")

    def get_key(self, message):
        if message["entity"] == "artists":
            return "artist_mbid"
        elif message["entity"] == "releases":
            return "release_mbid"
        elif message["entity"] == "release_groups":
            return "release_group_mbid"
        else:
            return "recording_mbid"

EntityListenerStatsDataset = _EntityListenerStatsDataset()


class DatabaseDataset(SparkDataset, ABC):
    """ A base class that makes it simple to setup swap tables workflow for datasets generated
    in spark and stored in timescale db.

    When we start receiving the dataset, we create a temporary table to store the data. Once
    the dataset has been received completely, we switch the temporary table with the production tables.
    We do not use something like INSERT ON CONFLICT DO NOTHING to avoid mixups the last runs' results
    (like tags being deleted since then).
    """

    def __init__(self, name, table_name, schema=None):
        super().__init__(name)
        self.base_table_name = table_name
        self.schema = schema

    def _get_table_name(self, suffix=None, exclude_schema=False):
        if suffix is None:
            table_name = self.base_table_name
        else:
            table_name = f"{self.base_table_name}_{suffix}"

        if self.schema is None or exclude_schema:
            return Identifier(table_name)
        else:
            return Identifier(self.schema, table_name)

    @abc.abstractmethod
    def get_table(self):
        """ Return the table query to create the table for storing this dataset.

            Note that the table name will be substituted later and should be specified as {table} in the query.
        """
        raise NotImplementedError()

    def get_indices(self):
        """ Return a list of indices to create on the dataset table.

        Each item in the list should be a CREATE INDEX statement with a {suffix} and {table} marker that will be later
        formatted by the caller.
        """
        return []

    @abc.abstractmethod
    def get_inserts(self, message):
        """ Return the query and the template along with the rows to be inserted into the database using them.

        Note that insert query should have a {table} marker to subsitute the name in it later and must have a
        VALUES %s clause.
        """
        raise NotImplementedError()

    def run_post_processing(self, cursor, message):
        """ Called after the rotate table swap is complete so that the user can execute any post processing steps. """
        pass

    def create_table(self, cursor):
        tmp_table = self._get_table_name("tmp")
        query = SQL("DROP TABLE IF EXISTS {table}").format(table=tmp_table)
        cursor.execute(query)

        query = self.get_table()
        if not isinstance(query, Composable):
            query = SQL(query).format(table=tmp_table)
        cursor.execute(query)

    def create_indices(self, cursor):
        tmp_table = self._get_table_name("tmp")
        # add a random suffix to the index name to avoid issues while renaming
        suffix = int(time.time())

        for index in self.get_indices():
            query = SQL(index).format(table=tmp_table, suffix=Literal(suffix))
            cursor.execute(query)

    def rotate_tables(self, cursor):
        query = SQL("ALTER TABLE IF EXISTS {prod_table} RENAME TO {outgoing_table}").format(
            prod_table=self._get_table_name(),
            outgoing_table=self._get_table_name(suffix="old", exclude_schema=True)
        )
        cursor.execute(query)

        query = SQL("ALTER TABLE IF EXISTS {incoming_table} RENAME TO {prod_table} ").format(
            incoming_table=self._get_table_name("tmp"),
            prod_table=self._get_table_name(exclude_schema=True)
        )
        cursor.execute(query)

        query = SQL("DROP TABLE IF EXISTS {old_table}").format(old_table=self._get_table_name(suffix="old"))
        cursor.execute(query)

    def handle_start(self, message):
        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                self.create_table(curs)
            conn.commit()
        finally:
            conn.close()

    def handle_end(self, message):
        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                self.create_indices(curs)
                self.rotate_tables(curs)
                self.run_post_processing(curs, message)
            conn.commit()
        finally:
            conn.close()

    def handle_insert(self, message):
        query, template, values = self.get_inserts(message)

        if not isinstance(query, Composable):
            tmp_table = self._get_table_name("tmp")
            query = SQL(query).format(table=tmp_table)

        if isinstance(template, str):
            template = SQL(template)

        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                execute_values(curs, query, values, template)
            conn.commit()
        finally:
            conn.close()
