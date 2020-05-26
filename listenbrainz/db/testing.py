
import os
import unittest

from listenbrainz import config
from listenbrainz import db

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'admin', 'sql')
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'testdata')


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        self.config = config
        db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
        self.reset_db()

    def tearDown(self):
        self.drop_tables()

    def reset_db(self):
        self.drop_tables()
        self.init_db()

    def init_db(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_schema.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    def drop_tables(self):
        self.drop_schema()
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_tables.sql'))

    def drop_schema(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'drop_schema.sql'))

    def path_to_data_file(self, file_name):
        """ Returns the path of the test data file relative to listenbrainz/db/testing.py.

            Args:
                file_name: the name of the data file
        """
        return os.path.join(TEST_DATA_PATH, file_name)
