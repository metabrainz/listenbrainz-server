from abc import abstractmethod

import psycopg2
from psycopg2.errors import OperationalError
from mapping.utils import insert_rows, log

BATCH_SIZE = 5000


class BulkInsertTable:
    """
        Manage a bulk insert table with this class by providing only the table
        definition, index definitions, post processing queries and row processing
        function. The class will handle the insertion into a tmp table, creating indexes
        on the temp table and finally swapping the table into production seamlessly.
    """

    def __init__(self, table_name, mb_conn, lb_conn=None, batch_size=None):
        """
            This init function expects to be passed a database connection (usually to MB)
            and an optional DB connection to ListenBrainz. If the lb_conn is passed in,
            the newly written table will be written to that database and the mb_conn connection
            will only be used to fetch the data.

            batch_size can also be specified, which controls how often to insert collected
            rows into the DB and the commit. The default setting should be fine in most cases.
        """

        self.table_name = table_name
        self.temp_table_name = table_name + "_TMP"
        self.mb_conn = mb_conn
        self.lb_conn = lb_conn

        if batch_size is None:
            batch_size = BATCH_SIZE
        self.batch_size = batch_size

    @abstractmethod
    def get_create_table_columns(self):
        """
            Return the PG query to fetch the insert data. This function should return
            a list of tuples of two strings: [(column name, column type/constraints/defaults)]
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
    def get_post_process_queries(self):
        """
            Returns an optional list of queries that should be run, sequentially, after the data has been
            inserted to the table, but before indexes are created.
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
    def process_row(self):
        """
            This function will be called for each of the rows fetch from the source DB. This function
            should return an empty list if there are no rows to insert, or a list of rows (in correct
            column order suitable for inserting data into the DB with psycopg2's execute_values call).
        """

    def _create_tables(self):
        """
            This function creates the temp table, given the provided specification.
        """


        # drop/create finished table
        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        try:
            with conn.cursor() as curs:

                columns = []
                for name, types in self.get_create_table_columns():
                    columns.append("%s %s" % (name, types))

                columns = ", ".join(columns)

                curs.execute(f"DROP TABLE IF EXISTS {self.temp_table_name}")
                curs.execute(f"CREATE TABLE {self.temp_table_name} ({columns})")
                conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to create tables", err)
            conn.rollback()
            raise

    def _create_indexes(self, no_analyze=False):
        """
            Create indexes on the created temp tables. If no_analyze is passed, do not 
            ANALYZE the created table.
        """

        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        try:
            with conn.cursor() as curs:
                for name, column_def in self.get_create_index_queries():
                    curs.execute(f"CREATE INDEX {name}_tmp ON {self.temp_table_name} ({column_def})")

                for name, types in self.get_create_table_columns():
                    if name == 'id' and types == "SERIAL":
                        log(f"{self.table_name}: set sequence value")
                        curs.execute(f"""SELECT setval('{self.temp_table_name}_id_seq', max(id) + 1, false)
                                           FROM {self.temp_table_name}""")
                        break

                if not no_analyze:
                    log(f"{self.table_name}: analyze table")
                    curs.execute(f"ANALYZE {self.temp_table_name}") 

                conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to create indexes", err)
            conn.rollback()
            raise

    def _post_process(self):
        """
            Run queries that do post insert cleanup/processing. These queries are run
            BEFORE indexes are created. Can be used for deduping created data, for instance.
        """

        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        try:
            with conn.cursor() as curs:
                for query in self.get_post_process_queries():
                    curs.execute(query)
                conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to post process queries", err)
            conn.rollback()
            raise


    def _swap_into_production(self, no_swap_transaction=False):
        """
            Delete the old table and swap temp table into its place, carefully renaming
            indexes and the if an id sequence exist, renaming it as well.

            If no_swap_transaction is True, then no commits will be carried out in
            this function and the caller must carry out the transaction manaagement
            for this function. This is useful for if two or more tables need to be
            swapped into production in a single transaction.
        """

        try:
            schema, simple_table_name = self.table_name.split(".")
        except ValueError:
            schema = ""
            simple_table_name = self.table_name

        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        try:
            with conn.cursor() as curs:
                curs.execute(f"DROP TABLE IF EXISTS {self.table_name}")
                curs.execute(f"ALTER TABLE {self.temp_table_name} RENAME TO {simple_table_name}") 
                for name, column_def in self.get_create_index_queries():
                    if schema:
                        curs.execute(f"ALTER INDEX {schema}.{name}_tmp RENAME TO {name}")
                    else:
                        curs.execute(f"ALTER INDEX {name}_tmp RENAME TO {name}")
                curs.execute(f"ALTER SEQUENCE IF EXISTS {self.temp_table_name}_id_seq RENAME TO {simple_table_name}_id_seq") 

                if not no_swap_transaction:
                    conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to swap into production", err)
            if not no_swap_transaction:
                conn.rollback()
            raise


    def run(self, no_swap_transaction=False, no_analyze=False):
        """
            The main loop of the class that carefully executes the provded statements
            and prints statistics about its progress.
        """

        log(f"{self.table_name}: start")
        log(f"{self.table_name}: drop old tables, create new tables")
        self._create_tables()

        conn = self.lb_conn if self.lb_conn is not None else self.mb_conn
        with self.mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ins_curs:
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
                            insert_rows(ins_curs, self.temp_table_name, rows)
                            self.mb_conn.commit()
                            rows = []
                            batch_count +=1
                            inserted += self.batch_size
                            inserted_total += self.batch_size

                            if batch_count % 20 == 0:
                                percent = "%.1f" % (100.0 * row_count / total_rows)
                                log(f"{self.table_name}: inserted {inserted:,} from {row_count:,} rows. {percent}% complete")

                if rows:
                    insert_rows(ins_curs, self.temp_table_name, rows)
                    conn.commit()
                    inserted_total += len(rows)
                    rows = []

        log(f"{self.table_name}: complete! inserted {inserted_total:,} rows total.")

        log(f"{self.table_name}: post process inserted rows")
        self._post_process()

        log(f"{self.table_name}: create indexes")
        self._create_indexes(no_analyze)

        log(f"{self.table_name}: swap tables and indexes into production.")
        self._swap_into_production(no_swap_transaction)

        log(f"{self.table_name}: done")
