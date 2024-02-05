
import os
import unittest

import sqlalchemy
import uuid

from listenbrainz import config
from listenbrainz import db
from listenbrainz.db import timescale as ts, create_test_database_connect_strings
from listenbrainz.db.timescale import create_test_timescale_connect_strings

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'admin', 'sql')
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'testdata')
TIMESCALE_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'admin', 'timescale')


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        db_connect = create_test_database_connect_strings()
        db.init_db_connection(db_connect["DB_CONNECT"])
        self.db_conn = db.engine.connect()

    def tearDown(self):
        self.db_conn.close()
        self.reset_db()

    def reset_db(self):
        db.run_sql_script(os.path.join(ADMIN_SQL_DIR, 'reset_tables.sql'))

    @classmethod
    def path_to_data_file(self, file_name):
        """ Returns the path of the test data file relative to listenbrainz/db/testing.py.

            Args:
                file_name: the name of the data file
        """
        return os.path.join(TEST_DATA_PATH, file_name)

    def create_user_with_id(self, lb_id: int, musicbrainz_row_id: int, musicbrainz_id: str):
        """ Create a new user with the specified LB id. """
        self.db_conn.execute(sqlalchemy.text("""
            INSERT INTO "user" (id, musicbrainz_id, musicbrainz_row_id, auth_token)
                 VALUES (:id, :mb_id, :mb_row_id, :token)
            ON CONFLICT (musicbrainz_id) DO NOTHING 
        """), {
            "id": lb_id,
            "mb_id": musicbrainz_id,
            "token": str(uuid.uuid4()),
            "mb_row_id": musicbrainz_row_id,
        })
        self.db_conn.commit()


class TimescaleTestCase(unittest.TestCase):

    def setUp(self):
        # Reset the database in setUp, this way if there is a test failure and you want
        # to inspect data, it won't have been cleared away
        ts_connect = create_test_timescale_connect_strings()
        ts.init_db_connection(ts_connect["DB_CONNECT"])
        self.reset_timescale_db()
        self.ts_conn = ts.engine.connect()

    def tearDown(self):
        self.ts_conn.close()

    def reset_timescale_db(self):
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'reset_tables.sql'))
