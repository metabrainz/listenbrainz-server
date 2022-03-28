from abc import abstractmethod

import psycopg2
from psycopg2.errors import OperationalError
from mapping.utils import insert_rows, log

BATCH_SIZE = 5000


class BulkInsertTable

    def __init__(self, table_name, mb_conn, lb_conn, batch_size=BATCH_SIZE):
        self.table_name = table_name
        self.tmp_table_name = table_name + "_TMP"
        self.mb_conn = mb_conn
        self.lb_conn = lb_conn


    # TODO: use lb_conn when needed
    # Add support for an auto serial column
    @abstractmethod
    def get_create_table_columns(self)
        """
            Return the PG query to fetch the insert data. This function should return
            a liost of tuples of two strings: [(column name, column type/constraints/defaults)]
        """

    @abstractmethod
    def get_insert_data_query(self)
        """
        """

    @abstractmethod
    def get_create_index_queries(self)
        """
            Returns a list of of tuples of index names and column defintion strings:
                [("mbid_mapping_ndx_recording_mbid", "recoding_mbid")]
        """

    @abstractmethod
    def get_post_process_queries(self)
        """
        """

    @abstractmethod
    def process_row(self)
        """
        """

    def _create_tables(self):
        """
            Create tables needed to create the recording artist pairs. First
            is the temp table that the results will be stored in (in order
            to not conflict with the production version of this table).
            Second its format sort table to enables us to sort releases
            according to preferred format, release date and type.
        """

        # drop/create finished table
        try:
            with self.mb_conn.cursor() as curs:

                columns = ""
                for name, types in self.get_create_table_columns():
                    columns += "%s,%s" % (name, types)

                curs.execute(f"DROP TABLE IF EXISTS {self.tmp_table_name}")
                curs.execute(f"CREATE TABLE {self.tmp_table_name} ({columns})")
                self.mb_conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to create tables", err)
            self.mb_conn.rollback()
            raise

    def _create_indexes(self):
        """
        """

        try:
            with self.mb_conn.cursor() as curs:
                for name, column_def in self.get_create_index_queries():
                    curs.execute(f"CREATE INDEX {self.name}_TMP ON {self.tmp_table_name} ({column_def})")
                self.mb_conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to create indexes", err)
            self.mb_conn.rollback()
            raise

    def _post_process(self):
        """
            Run queries that do post insert cleanup/processing. These queries are run
            BEFORE indexes are created.
        """

        try:
            with self.mb_conn.cursor() as curs:
                for query in self.get_post_process_queries():
                    curs.execute(query)
                self.mb_conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to post process queries", err)
            self.mb_conn.rollback()
            raise


    def _swap_into_production(self):
        """
            Delete the old table and swap temp table into its place.
        """

        try:
            with self.mb_conn.cursor() as curs:
                curs.execute(f"DROP TABLE IF EXISTS {self.table_name}")
                curs.execute(f"ALTER TABLE {self.tmp_table_name} RENAME TO {self.table_name}") 
                for name, column_def in self.get_create_index_queries():
                    curs.execute(f"ALTER INDEX {name}_TMP RENAME TO {name}")
                self.mb_conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to swap into production", err)
            self.mb_conn.rollback()
            raise


    def run(mb_conn, mb_curs):
        """
        """

        log(f"{self.table_name}: start")
        log(f"{self.table_name}: drop old tables, create new tables")
        self._create_tables()

        with mb_conn.cursor() as mb_curs2:
            log(f"{self.table_name}: execute query")
            mb_curs.execute(self.get_insert_query())

            log(f"{self.table_name}: fetch rows")
            total_rows = mb_curs.rowcount
            row_count = 0
            rows = []
            batch_count = 0
            while True:
                row = mb_curs.fetchone()
                if not row:
                    break

                rows_to_insert = self._process_row(row)
                rows.extend(rows_to_insert)
                row_count += len(rows_to_insert)
                if len(rows) >= self.batch_size:
                    insert_rows(mb_curs2, self.temp_table_name, rows)
                    mb_conn.commit()
                    rows = []
                    batch_count +=1

                    if batch_count % 20 == 0:
                        percent = "%.1f" % (100.0 * row_count / total_rows)
                        log(f"{self.table_name}: inserted {row_count:,} rows. {percent}% complete")

            if rows:
                insert_rows(mb_curs2, self.temp_table_name, rows)
                mb_conn.commit()
                rows = []

        log(f"{self.table_name}: inserted {row_count:,} rows total.")
        log(f"{self.table_name}: create indexes")
        create_indexes(mb_conn)

        log(f"{self.table_name}: swap tables and indexes into production.")
        swap_table_and_indexes(mb_conn)

        log(f"{self.table_name}: create canonical release table")
        create_canonical_release_table(mb_conn)

        log(f"{self.table_name}: done")
