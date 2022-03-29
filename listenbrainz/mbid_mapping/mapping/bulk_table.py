from abc import abstractmethod

import psycopg2
from psycopg2.errors import OperationalError
from mapping.utils import insert_rows, log

BATCH_SIZE = 5000


class BulkInsertTable:

    def __init__(self, table_name, mb_conn, lb_conn=None, batch_size=None):
        self.table_name = table_name
        self.temp_table_name = table_name + "_TMP"
        self.mb_conn = mb_conn
        self.lb_conn = lb_conn

        if batch_size is None:
            batch_size = BATCH_SIZE
        self.batch_size = batch_size



    # TODO: use lb_conn when needed
    # Add support for client side transactions on swap

    @abstractmethod
    def get_create_table_columns(self):
        """
            Return the PG query to fetch the insert data. This function should return
            a liost of tuples of two strings: [(column name, column type/constraints/defaults)]
        """
        return []

    @abstractmethod
    def get_insert_queries(self):
        """
            Returns a list of data insert queries to run. The same process_row function will be 
            called for each of the rows resulting from the passed queries.
        """
        return []

    @abstractmethod
    def get_create_index_queries(self):
        """
            Returns a list of of tuples of index names and column defintion strings:
                [("mbid_mapping_ndx_recording_mbid", "recoding_mbid")]
        """
        return []

    @abstractmethod
    def get_post_process_queries(self):
        """
        """
        return []

    @abstractmethod
    def process_row(self):
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

                columns = []
                for name, types in self.get_create_table_columns():
                    columns.append("%s %s" % (name, types))

                columns = ", ".join(columns)

                curs.execute(f"DROP TABLE IF EXISTS {self.temp_table_name}")
                curs.execute(f"CREATE TABLE {self.temp_table_name} ({columns})")
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
                    curs.execute(f"CREATE INDEX {name}_tmp ON {self.temp_table_name} ({column_def})")

                for name, types in self.get_create_table_columns():
                    if name == 'id' and types == "SERIAL":
                        log(f"{self.table_name}: set sequence value")
                        curs.execute(f"""SELECT setval('{self.temp_table_name}_id_seq', max(id) + 1, false)
                                           FROM {self.temp_table_name}""")
                        break

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
            schema, simple_table_name = self.table_name.split(".")
        except ValueError:
            schema = ""
            simple_table_name = self.table_name

        try:
            with self.mb_conn.cursor() as curs:
                curs.execute(f"DROP TABLE IF EXISTS {self.table_name}")
                curs.execute(f"ALTER TABLE {self.temp_table_name} RENAME TO {simple_table_name}") 
                for name, column_def in self.get_create_index_queries():
                    if schema:
                        curs.execute(f"ALTER INDEX {schema}.{name}_tmp RENAME TO {name}")
                    else:
                        curs.execute(f"ALTER INDEX {name}_tmp RENAME TO {name}")
                curs.execute(f"ALTER SEQUENCE IF EXISTS {self.temp_table_name}_id_seq RENAME TO {simple_table_name}_id_seq") 
                self.mb_conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to swap into production", err)
            self.mb_conn.rollback()
            raise


    def run(self):
        """
        """

        log(f"{self.table_name}: start")
        log(f"{self.table_name}: drop old tables, create new tables")
        self._create_tables()

        with self.mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            with self.mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs2:
                queries = self.get_insert_queries()
                total_row_count = 0
                rows = []
                inserted = 0
                inserted_total = 0
                batch_count = 0
                for i, query in enumerate(queries):
                    log(f"{self.table_name}: execute query {i+1} of {len(queries)}")
                    mb_curs.execute(query)

                    row_count = 0
                    inserted = 0
                    total_rows = mb_curs.rowcount
                    log(f"{self.table_name}: fetch {total_rows:,} rows")
                    while True:
                        row = mb_curs.fetchone()
                        if not row:
                            break

                        row_count += 1
                        total_row_count += 1
                        rows.extend(self.process_row(row))
                        if len(rows) >= self.batch_size:
                            insert_rows(mb_curs2, self.temp_table_name, rows)
                            self.mb_conn.commit()
                            rows = []
                            batch_count +=1
                            inserted += self.batch_size
                            inserted_total += self.batch_size

                            if batch_count % 20 == 0:
                                percent = "%.1f" % (100.0 * row_count / total_rows)
                                log(f"{self.table_name}: inserted {inserted:,} from {row_count:,} rows. {percent}% complete")

                if rows:
                    insert_rows(mb_curs2, self.temp_table_name, rows)
                    self.mb_conn.commit()
                    inserted_total += len(rows)
                    rows = []

        log(f"{self.table_name}: complete! inserted {inserted_total:,} rows total.")

        log(f"{self.table_name}: post process inserted rows")
        self._post_process()

        log(f"{self.table_name}: create indexes")
        self._create_indexes()

        log(f"{self.table_name}: swap tables and indexes into production.")
        self._swap_into_production()

        log(f"{self.table_name}: done")
