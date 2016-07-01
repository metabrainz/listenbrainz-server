import db
import unittest
import json
import os

# Configuration
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'admin', 'sql')
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data')


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        db.init_db_connection(config.TEST_SQLALCHEMY_DATABASE_URI)
        self.reset_db()

    def tearDown(self):
        pass

    def reset_db(self):
        self.drop_tables()
        self.init_db()

    def init_db(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    def drop_tables(self):
        with db.engine.connect() as connection:
            connection.execute('DROP TABLE IF EXISTS "user"       CASCADE')
            connection.execute('DROP TABLE IF EXISTS listen       CASCADE')

    def load_data_files(self, mbid):
        """ Get the data files from the disk """
        # return os.path.join(TEST_DATA_PATH, mbid + '.json')
        return
