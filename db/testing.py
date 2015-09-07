from db import run_sql_script, create_cursor, commit, init_db_connection
import unittest
import os

# Configuration
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data')


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        init_db_connection(config.PG_CONNECT_TEST)
        self.reset_db()

    def tearDown(self):
        pass

    def reset_db(self):
        self.drop_tables()
        self.init_db()

    def init_db(self):
        run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
        run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    def drop_tables(self):
        with create_cursor() as cursor:
            # TODO(roman): See if there's a better way to drop all tables.
            # FIXME: Need to drop all tables that we have there.
            #cursor.execute('DROP TABLE IF EXISTS i_am_a_table CASCADE;')
            pass
        commit()
