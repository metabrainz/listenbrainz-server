# coding=utf-8

import listenbrainz.db.user as db_user
import logging
import os
import tempfile
import ujson

from datetime import datetime
from collections import OrderedDict
from influxdb import InfluxDBClient
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listen import Listen
from listenbrainz.listenstore import InfluxListenStore
from listenbrainz.listenstore.tests.util import create_test_data_for_influxlistenstore
from listenbrainz.webserver.influx_connection import init_influx_connection
from sqlalchemy import text
from time import sleep

from listenbrainz import default_config as config
try:
    from listenbrainz import custom_config as config
except ImportError:
    pass


class TestInfluxListenStore(DatabaseTestCase):


    def reset_influx_db(self):
        """ Resets the entire influx db """
        influx = InfluxDBClient(
            host=config.INFLUX_HOST,
            port=config.INFLUX_PORT,
            database=config.INFLUX_DB_NAME
        )
        influx.query('DROP DATABASE %s' % config.INFLUX_DB_NAME)
        influx.query('CREATE DATABASE %s' % config.INFLUX_DB_NAME)


    def setUp(self):
        super(TestInfluxListenStore, self).setUp()
        self.log = logging.getLogger(__name__)

        # In order to do counting correctly, we need a clean DB to start with
        self.reset_influx_db()

        self.logstore = init_influx_connection(self.log, {
            'REDIS_HOST': config.REDIS_HOST,
            'REDIS_PORT': config.REDIS_PORT,
            'INFLUX_HOST': config.INFLUX_HOST,
            'INFLUX_PORT': config.INFLUX_PORT,
            'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
        })
        self.testuser_id = db_user.create("test")
        self.testuser_name = db_user.get(self.testuser_id)['musicbrainz_id']

    def tearDown(self):
        self.logstore = None
        super(TestInfluxListenStore, self).tearDown()

    def _create_test_data(self, user_name):
        test_data = create_test_data_for_influxlistenstore(user_name)
        self.logstore.insert(test_data)
        return len(test_data)

    # this test should be done first, because the other tests keep inserting more rows
    def test_aaa_get_total_listen_count(self):
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(0, listen_count)

        count = self._create_test_data(self.testuser_name)
        sleep(1)
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(count, listen_count)

        self.logstore.update_listen_counts()
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(count, listen_count)

        count = self._create_test_data(self.testuser_name)
        sleep(1)
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(count * 2, listen_count)

        self.logstore.update_listen_counts()
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(count * 2, listen_count)

    def test_insert_influx(self):
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

    def test_get_listen_count_for_user(self):
        count = self._create_test_data(self.testuser_name)
        self.logstore.update_listen_counts()
        listen_count = self.logstore.get_listen_count_for_user(user_name=self.testuser_name)
        self.assertEqual(count, listen_count)

    def test_fetch_listens_escaped(self):
        user = db_user.get_or_create('i have a\\weird\\user, name"\n')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name)
        listens = self.logstore.fetch_listens(user_name=user_name, from_ts=1400000100)
        self.assertEquals(len(listens), 2)
        self.assertEquals(listens[0].ts_since_epoch, 1400000200)
        self.assertEquals(listens[1].ts_since_epoch, 1400000150)


    def test_dump_listens(self):
        self._create_test_data(self.testuser_name)
        temp_dir = tempfile.mkdtemp()
        dump = self.logstore.dump_listens(
            location=temp_dir,
        )
        self.assertTrue(os.path.isfile(dump))


    def test_import_listens(self):
        count = self._create_test_data(self.testuser_name)
        sleep(1)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_influx_db()

        sleep(1)
        self.logstore.import_listens_dump(dump_location)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

    def test_dump_and_import_listens_escaped(self):
        user = db_user.get_or_create('i have a\\weird\\user, na/me"\n')
        count = self._create_test_data(user['musicbrainz_id'])
        sleep(1)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_influx_db()

        sleep(1)
        self.logstore.import_listens_dump(dump_location)
        listens = self.logstore.fetch_listens(user_name=user['musicbrainz_id'], to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)
