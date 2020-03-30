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


TIMESCALE_SQL_DIR = "/code/listenbrainz/admin/timescale"

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
        })

        self.testuser_id = db_user.create(1, "test")
        self.testuser_name = db_user.get(self.testuser_id)['musicbrainz_id']


    def _create_test_data(self, user_name):
        test_data = create_test_data_for_influxlistenstore(user_name)
        self.logstore.insert(test_data)
        return len(test_data)

    def test_get_listen_count_for_user(self):
        count = self._create_test_data(self.testuser_name)
        listen_count = self.logstore.get_listen_count_for_user(user_name=self.testuser_name)
        self.assertEqual(count, listen_count)