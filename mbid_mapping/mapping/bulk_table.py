from abc import abstractmethod
from itertools import zip_longest

import psycopg2
from psycopg2.extras import DictCursor, execute_values
from tqdm import tqdm
from mapping.utils import insert_rows, log

BATCH_SIZE = 5000


class BulkInsertTable:
    """
        Manage a bulk insert table with this class by providing only the table
        definition, index definitions, post processing queries and row processing
        function. The class will handle the insertion into a tmp table, creating indexes
        on the temp table and finally swapping the table into production seamlessly.
    """

    def __init__(self, table_name, select_conn, insert_conn=None, batch_size=None, unlogged=None):
        """
            This init function expects to be passed a database connection to read data from (usually MB)
            and an optional DB connection to write data to (usually ListenBrainz). If the insert_conn is
            passed in, the newly written table will be written to that database and the select_conn connection
            will only be used to fetch the data. However, if insert_conn is not passed in, the select_conn
            will also be used to write the data.

            batch_size can also be specified, which controls how often to insert collected
            rows into the DB and the commit. The default setting should be fine in most cases.
        """

        self.table_name = table_name
        self.temp_table_name = table_name + "_TMP"
        self.select_conn = select_conn
        self.insert_conn = insert_conn if insert_conn is not None else select_conn
        self.insert_columns = []

        # For use with additional tables
        self.additional_tables = []
        self.insert_rows = []

        if batch_size is None:
            batch_size = BATCH_SIZE
        self.batch_size = batch_size
        self.total_rows = 0

        self.unlogged = unlogged

    def add_additional_bulk_table(self, bulk_table):
        """
            Sometimes a bulk insert table query can generate output for more than one table.
            By adding more bulk-tables to this table, this class will drive the creation of
            all the tables related to this table. If you add another bulk table, you should
            not call run() on the additional tables. This class will manage the creation process
            but the process_row() function of additional tables will not be called since
            additional tables are assumed to be inserting data createed by the primary table.
        """
        self.additional_tables.append(bulk_table)

    @abstractmethod
    def get_create_table_columns(self):
        """
            Return the names and column types of the table to be created. This function should return a list
            of tuples of two strings: [(column name, column type/constraints/defaults)]
        """
        return []

    @abstractmethod
    def get_insert_queries(self):
        """
            Returns a list of data insert queries to run.
            The process_row function will be called for each of the rows resulting from the queries.

            Example:
                ["SELECT * from ...", "SELECT * from ... "]
        """
        return []

    def get_insert_queries_test_values(self):
        """
            Return test query values. In order to facilitate debugging, it is sometimes useful to run a query
            on a subset of data, usually specified with an IN clause in a postgres query. If this function
            is overridden in your class and returns anything other than a non-empty list, a test version of the
            query will be run using psycopg2's execute_values function, rather than the standard execute method
            of the cursor.

            Test data returned by this function should be a list of lists, where each outer list corresponds
            to the query returned by get_insert_queries() so that the correct test values can be used with each of the 
            queries to be executed. The inner list is a list of VALUES that are expected as part of the query.
        """
        return []

    def pre_insert_queries_db_setup(self, curs):
        """
            If any particular database setup needs to be done before the insert queries are run, define this
            method in your class. It will be called before the SQL statement is executed.
        """
        pass

    @abstractmethod
    def get_post_process_queries(self):
        """
            Returns an optional list of queries that should be run, sequentially, after the data has been
            inserted to the table, but before indexes are created.
        """
        return []

    @abstractmethod
    def get_index_names(self):
        """
            Returns a list of of tuples of (index names, column defintion, unique) strings:
                [("mbid_mapping_ndx_recording_mbid", "recoding_mbid", True)]
            Will create the unique index mbid_mapping_ndx_recording_mbid on recording_mbid.
        """
        return []

    @abstractmethod
    def process_row(self, row):
        """
            This function will be called for each of the rows fetch from the source DB. This function
            should return an empty list if there are no rows to insert, or a list of rows (in correct
            column order suitable for inserting data into the DB with psycopg2's execute_values call).

            If an additional table has been added to this bulk table, process_row should return a
            dict as follows instead:
                { "mapping.mbid_mapping": [ ... row data ... ],
                  "mapping.canonical_recording": [ ... row data ... ] }

            The dict keys must be the name of the main or one of the additional tables. Rows will
            be inserted into the correct table.
        """

    @abstractmethod
    def process_row_complete(self):
        """
            This function will be called after the last row has been sent to process_row, so that
            any flushing/cleanup needed can be completed.
        """
        return []

    def table_exists(self):
        """Check if the table for this bulk inserter exists.

        Returns:
            True if it exists and has data in it
            False if it doesn't exist or is empty
        """
        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        try:
            with conn.cursor() as curs:
                query = f"SELECT 1 FROM {self.table_name} LIMIT 1"
                curs.execute(query)
                if curs.rowcount > 0:
                    return True
                else:
                    return False
        except psycopg2.errors.UndefinedTable as err:
            return False

    def _create_tables(self):
        """
            This function creates the temp table, given the provided specification.
        """
        conn = self.insert_conn if self.insert_conn is not None else self.select_conn

        # drop/create finished table
        try:
            with conn.cursor() as curs:
                if "." in self.table_name:
                    # the savepoint is needed because otherwise the transaction will be aborted
                    # if a privilege error occurs
                    savepoint = "try_creating_schema"
                    schema = self.table_name.split(".")[0]
                    try:
                        curs.execute(f"SAVEPOINT {savepoint}")
                        curs.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                        curs.execute(f"RELEASE SAVEPOINT {savepoint}")
                    # silently ignore schema creation errors because the user in prod
                    # doesn't have sufficient privileges
                    except psycopg2.errors.InsufficientPrivilege as err:
                        curs.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")

                columns = []
                for name, types in self.get_create_table_columns():
                    columns.append("%s %s" % (name, types))
                    if name != "id" and types != "SERIAL":
                        self.insert_columns.append(name)

                columns = ", ".join(columns)

                curs.execute(f"DROP TABLE IF EXISTS {self.temp_table_name}")
                curs.execute(f"CREATE {'UNLOGGED' if self.unlogged else ''} TABLE {self.temp_table_name} ({columns})")
                conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to create tables", err)
            conn.rollback()
            raise

        # Now chain this call to additional tables
        for table in self.additional_tables:
            table._create_tables()

    def _create_indexes(self, no_analyze=False):
        """
            Create indexes on the created temp tables. If no_analyze is passed, do not
            ANALYZE the created table.
        """

        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        try:
            with conn.cursor() as curs:
                for name, column_def, unique in self.get_index_names():
                    uniq = "UNIQUE" if unique else ""
                    if column_def.find("(") == -1:
                        column_def = "(" + column_def + ")"
                    curs.execute(f"CREATE {uniq} INDEX {name}_tmp ON {self.temp_table_name} {column_def}")

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

        # Now chain this call to additional tables
        for table in self.additional_tables:
            table._create_indexes(no_analyze)

    def _post_process(self):
        """
            Run queries that do post insert cleanup/processing. These queries are run
            BEFORE indexes are created. Can be used for deduping created data, for instance.
        """

        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        try:
            with conn.cursor() as curs:
                for query in self.get_post_process_queries():
                    curs.execute(query)
                conn.commit()

        except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
            log(f"{self.table_name}: failed to post process queries", err)
            conn.rollback()
            raise

        # Now chain this call to additional tables
        for table in self.additional_tables:
            table._post_process()

    def swap_into_production(self, no_swap_transaction=False, swap_conn=None):
        """
            Delete the old table and swap temp table into its place, carefully renaming
            indexes and the if an id sequence exist, renaming it as well.

            If no_swap_transaction is True, then no commits will be carried out in
            this function and the caller must carry out the transaction manaagement
            for this function. This is useful for if two or more tables need to be
            swapped into production in a single transaction. If this is specified
            additional tables must have their swap_into_production function called
            manually.
        """

        try:
            schema, simple_table_name = self.table_name.split(".")
        except ValueError:
            schema = ""
            simple_table_name = self.table_name

        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        conn = swap_conn if swap_conn is not None else conn
        try:
            with conn.cursor() as curs:
                curs.execute(f"DROP TABLE IF EXISTS {self.table_name}")
                curs.execute(f"ALTER TABLE {self.temp_table_name} RENAME TO {simple_table_name}")
                for name, column_def, _ in self.get_index_names():
                    if schema:
                        curs.execute(f"ALTER INDEX {schema}.{name}_tmp RENAME TO {name}")
                    else:
                        curs.execute(f"ALTER INDEX {name}_tmp RENAME TO {name}")
                curs.execute(f"ALTER SEQUENCE IF EXISTS {self.temp_table_name}_id_seq RENAME TO {simple_table_name}_id_seq")

                if not no_swap_transaction:
                    conn.commit()

        except psycopg2.Error as err:
            log(f"{self.table_name}: failed to swap into production", err)
            if not no_swap_transaction:
                conn.rollback()
            raise

        if not no_swap_transaction:
            for table in self.additional_tables:
                table.swap_into_production(no_swap_transaction)

    def _add_insert_rows(self, rows):
        """
            This function should only be called when this table is considered to be
            an additional bulk insert table and its rows have been generated by
            the higher level bulk insert table. Since additional tables will not have
            their process_row function called, this function takes its place for saving
            resultant rows in the table.
        """
        self.insert_rows.extend(rows)
        if len(self.insert_rows) >= self.batch_size:
            self._flush_insert_rows()

    def _flush_insert_rows(self):
        """
            This function should only be called when this table is considered to be
            an additional bulk insert table and the inserting of rows is complete.
            This function will flush out any remaining rows in ram to the DB.
        """

        conn = self.insert_conn if self.insert_conn is not None else self.select_conn
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ins_curs:
            insert_rows(ins_curs, self.temp_table_name, self.insert_rows, cols=self.insert_columns)
        conn.commit()
        self.insert_rows = []

    def _handle_result(self, result):
        """
            Helper function for routing rows to be inserted.
        """
        if result is None:
            return []

        ret = []
        if type(result) in (list, tuple):
            ret.extend(result)
        else:
            # Assume result is a dict with table names as the keys
            for key in result:
                if key == self.table_name:
                    ret.extend(result[key])
                else:
                    for table in self.additional_tables:
                        if table.table_name == key:
                            table._add_insert_rows(result[key])
                            break
                    else:
                        # We should never get here. If we do, we have rows and no idea what to do with them
                        assert False

        return ret

    def run(self, no_swap=False, no_analyze=False):
        """
            The main loop of the class that carefully executes the provded statements
            and prints statistics about its progress.

            Options:
               no_swap     - If True, do not call swap_into_production, the caller will do it
               no_analyze  - If True, do not run ANALYZE on the result table
        """

        log(f"{self.table_name}: start")
        log(f"{self.table_name}: drop old tables, create new tables")
        self._create_tables()

        total_row_count = 0
        rows = []
        inserted_total = 0
        batch_count = 0

        with self.insert_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ins_curs:
            queries = self.get_insert_queries()
            values = self.get_insert_queries_test_values()

            for i, db_query_vals in enumerate(zip_longest(queries, values)):
                query = db_query_vals[0]
                vals = db_query_vals[1]

                if self.select_conn is None:
                    log("You need to provide a DB connections string.")
                    raise RuntimeError

                with self.select_conn.cursor(cursor_factory=DictCursor) as curs:
                    log(f"{self.table_name}: execute query {i+1} of {len(queries)}")
                    self.pre_insert_queries_db_setup(curs)
                    if vals:
                        execute_values(curs, query, vals, page_size=len(vals))
                    else:
                        curs.execute(query)

                    row_count = 0
                    inserted = 0
                    self.total_rows = curs.rowcount
                    log(f"{self.table_name}: fetch {self.total_rows:,} rows")
                    progress_bar = tqdm(total=self.total_rows)
                    while True:
                        batch = curs.fetchmany(BATCH_SIZE)
                        if len(batch) == 0:
                            break

                        for row in batch:
                            row_count += 1
                            total_row_count += 1
                            result = self.process_row(row)
                            progress_bar.update(1)
                            rows.extend(self._handle_result(result))

                        if len(rows) >= self.batch_size:
                            insert_rows(ins_curs, self.temp_table_name, rows, cols=self.insert_columns)
                            self.insert_conn.commit()
                            rows = []
                            batch_count += 1
                            inserted += self.batch_size
                            inserted_total += self.batch_size

                            if batch_count % 20 == 0:
                                percent = "%.1f" % (100.0 * row_count / self.total_rows)
                                log(f"{self.table_name}: inserted {inserted:,} from {row_count:,} rows. {percent}% complete")

                    progress_bar.close()

                rows.extend(self._handle_result(self.process_row_complete()))
                if rows:
                    insert_rows(ins_curs, self.temp_table_name, rows, cols=self.insert_columns)
                    self.insert_conn.commit()
                    inserted_total += len(rows)
                    rows = []

                for table in self.additional_tables:
                    table._flush_insert_rows()

        log(f"{self.table_name}: complete! inserted {inserted_total:,} rows total.")

        log(f"{self.table_name}: post process inserted rows")
        self._post_process()

        log(f"{self.table_name}: create indexes")
        self._create_indexes(no_analyze)

        if not no_swap:
            log(f"{self.table_name}: swap tables and indexes into production.")
            self.swap_into_production()
        else:
            log(f"{self.table_name}: defer swap tables.")

        log(f"{self.table_name}: done")
