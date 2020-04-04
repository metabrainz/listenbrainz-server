# coding=utf-8

import listenbrainz.db.user as db_user
import os
import time
import ujson
from time import sleep
import logging
import psycopg2
from psycopg2.extras import execute_values
import sqlalchemy

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import timescale as ts
from listenbrainz import config
from listenbrainz.listenstore.tests.util import create_test_data_for_influxlistenstore, generate_data
from listenbrainz.webserver.timescale_connection import init_ts_connection

TIMESCALE_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'admin', 'timescale')

class TestTimescaleListenStore(DatabaseTestCase):


    def reset_timescale_db(self):

        ts.init_db_connection(config.TIMESCALE_ADMIN_URI)
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'drop_db.sql'))
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_db.sql'))

        ts.init_db_connection(config.TIMESCALE_ADMIN_LB_URI)
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_extensions.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_tables.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_functions.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_views.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_indexes.sql'))


    def setUp(self):
        super(TestTimescaleListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.reset_timescale_db()
        
        self.logstore = init_ts_connection(self.log, {
            'REDIS_HOST': config.REDIS_HOST,
            'REDIS_PORT': config.REDIS_PORT,
            'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
            'SQLALCHEMY_TIMESCALE_URI': config.SQLALCHEMY_TIMESCALE_URI,
        })

        self.testuser_id = db_user.create(1, "test")
        self.testuser_name = db_user.get(self.testuser_id)['musicbrainz_id']

    def tearDown(self):
        self.logstore = None
        super(TestTimescaleListenStore, self).tearDown()

    def _create_test_data(self, user_name):
        test_data = create_test_data_for_influxlistenstore(user_name)
        self.logstore.insert(test_data)
        return len(test_data)

    def test_check_listen_count_view_exists(self):
        try:
            with ts.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'listen_count'"))
                cols = result.fetchall()
        except psycopg2.OperationalError as e:
            self.log.error("Cannot query timescale listen_count: %s" % str(e), exc_info=True)
            raise
        self.assertEqual(cols[0][0], "bucket")
        self.assertEqual(cols[1][0], "user_name")
        self.assertEqual(cols[2][0], "count")

    def test_insert_timescale(self):
        count = self._create_test_data(self.testuser_name)
        self.assertEqual(len(self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1399999999)), count)
    
    def test_fetch_listens_0(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000000, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000050)

    def test_fetch_listens_1(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000000)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)

    def test_fetch_listens_2(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000100)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_listens_3(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

#    def test_get_listen_count_for_user(self):
#        count = self._create_test_data(self.testuser_name)
#
#        # The listen_counts in the database will always be lagging behind and will not be fully
#        # accurate, but they will give a good indication for the number of listens of a user.
#        # This means that we can't insert data data and expect it to be in the DB right away
#        # so we can fetch them for running tests
#        listen_count = self.logstore.get_listen_count_for_user(user_name=self.testuser_name)
#        self.assertEqual(count, listen_count)

    def test_fetch_listens_escaped(self):
        user = db_user.get_or_create(2, 'i have a\\weird\\user, name"\n')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name)
        listens = self.logstore.fetch_listens(user_name=user_name, from_ts=1400000100)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_recent_listens(self): #fail
        user = db_user.get_or_create(2, 'someuser')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name)

        user2 = db_user.get_or_create(3, 'otheruser')
        user_name2 = user2['musicbrainz_id']
        self._create_test_data(user_name2)

        recent = self.logstore.fetch_recent_listens_for_users([user_name, user_name2], limit=1, max_age=10000000000)
        self.assertEqual(len(recent), 2)

        recent = self.logstore.fetch_recent_listens_for_users([user_name, user_name2], max_age=10000000000)
        self.assertEqual(len(recent), 4)

        recent = self.logstore.fetch_recent_listens_for_users([user_name], max_age = int(time.time()) - recent[0].ts_since_epoch + 1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].ts_since_epoch, 1400000200)
