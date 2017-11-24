# coding=utf-8

from listenbrainz.db.testing import DatabaseTestCase
import logging
from datetime import datetime
from listenbrainz.listenstore.tests.util import create_test_data_for_influxlistenstore
from listenbrainz.listen import Listen
from listenbrainz.listenstore import InfluxListenStore
from listenbrainz.webserver.influx_connection import init_influx_connection
from influxdb import InfluxDBClient
import random
import uuid
from collections import OrderedDict
from sqlalchemy import text
import ujson
import listenbrainz.db.user as db_user
from listenbrainz import config
from time import sleep


class TestInfluxListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestInfluxListenStore, self).setUp()
        self.log = logging.getLogger(__name__)

        # In order to do counting correctly, we need a clean DB to start with
        influx = InfluxDBClient(host=config.INFLUX_HOST, port=config.INFLUX_PORT, database=config.INFLUX_DB_NAME)
        influx.query('''drop database %s''' % config.INFLUX_DB_NAME)
        influx.query('''create database %s''' % config.INFLUX_DB_NAME)

        self.logstore = init_influx_connection(self.log, {
            'REDIS_HOST': config.REDIS_HOST,
            'REDIS_PORT': config.REDIS_PORT,
            'INFLUX_HOST': config.INFLUX_HOST,
            'INFLUX_PORT': config.INFLUX_PORT,
            'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
        })
        self.testuser_id = db_user.create("test")
        user = db_user.get(self.testuser_id)
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
        count = self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000000, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000050)

    def test_fetch_listens_1(self):
        count = self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000000)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)

    def test_fetch_listens_2(self):
        count = self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000100)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_listens_3(self):
        count = self._create_test_data(self.testuser_name)
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
        count = self._create_test_data(user_name)
        listens = self.logstore.fetch_listens(user_name=user_name, from_ts=1400000100)
        self.assertEquals(len(listens), 2)
        self.assertEquals(listens[0].ts_since_epoch, 1400000200)
        self.assertEquals(listens[1].ts_since_epoch, 1400000150)
