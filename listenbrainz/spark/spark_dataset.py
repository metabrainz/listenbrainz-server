import abc
import time
from abc import ABC
from urllib.error import HTTPError

from flask import current_app
from psycopg2.extras import execute_values
from psycopg2.sql import Identifier, SQL, Literal

from listenbrainz.db import couchdb, timescale


class SparkDataset(ABC):

    def __init__(self, name):
        self.name = name

    @abc.abstractmethod
    def handle_start(self, message):
        pass

    @abc.abstractmethod
    def handle_insert(self, message):
        pass

    @abc.abstractmethod
    def handle_end(self, message):
        pass

    def get_handlers(self):
        return {
            f"{self.name}_start": self.handle_start,
            self.name: self.handle_insert,
            f"{self.name}_end": self.handle_end
        }


class _CouchDbDataset(SparkDataset):

    def __init__(self):
        super().__init__(name="couchdb_data")

    def handle_start(self, message):
        match = couchdb.DATABASE_NAME_PATTERN.match(message["database"])
        if not match:
            return
        try:
            couchdb.create_database(match[1] + "_" + match[2] + "_" + match[3])
            if match[1] == "artists":
                couchdb.create_database("artistmap" + "_" + match[2] + "_" + match[3])
        except HTTPError as e:
            current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)

    def handle_insert(self, message):
        raise NotImplementedError()

    def handle_end(self, message):
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

            # when new artist stats received, also invalidate old artist map stats
            if match[1] == "artists":
                _, retained = couchdb.delete_database("artistmap" + "_" + match[2])
                if retained:
                    current_app.logger.info(f"Databases: {retained} matched but weren't deleted because"
                                            f" _LOCK file existed")

        except HTTPError as e:
            current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


CouchDbDataset = _CouchDbDataset()


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
            table_name = f"{self.base_table_name}_tmp"

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
        raise NotImplementedError()

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

        query = SQL(self.get_table()).format(table=tmp_table)
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
        tmp_table = self._get_table_name("tmp")
        query = SQL(query).format(tmp_table)
        template = SQL(template)

        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                execute_values(curs, query, values, template)
            conn.commit()
        finally:
            conn.close()
