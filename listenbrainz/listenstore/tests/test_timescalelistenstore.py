# coding=utf-8

import listenbrainz.db.user as db_user
import os
import time
import ujson
from time import sleep
import logging

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
        print("yup")
        self.reset_timescale_db()
        
        self.logstore = init_ts_connection(self.log, {
            'REDIS_HOST': config.REDIS_HOST,
            'REDIS_PORT': config.REDIS_PORT,
            'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
            'SQLALCHEMY_TIMESCALE_URI': config.SQLALCHEMY_TIMESCALE_URI,
        })

        self.testuser_id = db_user.create(1, "test")
        self.testuser_name = db_user.get(self.testuser_id)['musicbrainz_id']


    def _create_test_data(self, user_name):
        test_data = create_test_data_for_influxlistenstore(user_name)
        self.logstore.insert(test_data)
        return len(test_data)

    def test_insert_timescale(self):
        count = self._create_test_data(self.testuser_name)
        self.assertEqual(len(self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1399999999)), count)

#    def test_get_listen_count_for_user(self):
#        count = self._create_test_data(self.testuser_name)
#
#        # The listen_counts in the database will always be lagging behind and will not be fully
#        # accurate, but they will give a good indication for the number of listens of a user.
#        # This means that we can't insert data data and expect it to be in the DB right away
#        # so we can fetch them for running tests
#        listen_count = self.logstore.get_listen_count_for_user(user_name=self.testuser_name)
#        self.assertEqual(count, listen_count)
