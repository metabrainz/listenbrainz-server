
from listenbrainz import db
import unittest
import os
from listenbrainz import config

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..','admin', 'sql')
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data')


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        self.config = config
        db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
        self.reset_db()

    def tearDown(self):
        self.drop_tables()
        self.drop_schema()

    def reset_db(self):
        self.drop_tables()
        self.drop_schema()
        self.init_db()

    def init_db(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_schema.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_tables.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_primary_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_foreign_keys.sql'))
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'create_indexes.sql'))

    def drop_tables(self):
        with db.engine.connect() as connection:
            connection.execute('DROP TABLE IF EXISTS "user"              CASCADE')
            connection.execute('DROP TABLE IF EXISTS listen              CASCADE')
            connection.execute('DROP TABLE IF EXISTS listen_json         CASCADE')
            connection.execute('DROP TABLE IF EXISTS api_compat.token    CASCADE')
            connection.execute('DROP TABLE IF EXISTS api_compat.session  CASCADE')

    def drop_schema(self):
        with db.engine.connect() as connection:
            connection.execute('DROP SCHEMA IF EXISTS api_compat')

    def load_data_files(self):
        """ Get the data files from the disk """
        # return os.path.join(TEST_DATA_PATH, file_name)
        return
