# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from db.testing import DatabaseTestCase
import logging
from datetime import datetime
from .util import generate_data, to_epoch
from listen import Listen
from listenstore.listenstore import InfluxListenStore, MIN_ID
from webserver.influx_connection import init_influx_connection
import random
import uuid
from collections import OrderedDict
from sqlalchemy import text
import ujson
import db.user
import config

TEST_LISTEN_JSON = [
    """
    {
        "track_metadata": {
           "track_name": "Immigrant Song 0",
           "additional_info": {
              "recording_mbid": "2cfad207-3f55-4aec-8120-86cf66e34d59",
              "artist_msid": "e229c8fa-7450-4916-8848-4535a40dc151",
              "release_msid": null
           },
           "artist_name": "Led Zeppelin"
        },
        "user_id": 1,
        "listened_at": "1400000000",
        "user_name": "test",
        "recording_msid": "4269ddbc-9241-46da-935d-4fa9e0f7f371"
    }
    """,
    """
    {
        "track_metadata": {
           "track_name": "Immigrant Song 50",
           "additional_info": {
              "recording_mbid": "2cfad207-3f55-4aec-8120-86cf66e34d59",
              "artist_msid": "e229c8fa-7450-4916-8848-4535a40dc151",
              "release_msid": null
           },
           "artist_name": "Led Zeppelin"
        },
        "user_id": 1,
        "listened_at": "1400000050",
        "user_name": "test",
        "recording_msid": "4269ddbc-9241-46da-935d-4fa9e0f7f371"
    }
    """,
    """
    {
        "track_metadata": {
           "track_name": "Immigrant Song 100",
           "additional_info": {
              "recording_mbid": "2cfad207-3f55-4aec-8120-86cf66e34d59",
              "artist_msid": "e229c8fa-7450-4916-8848-4535a40dc151",
              "release_msid": null
           },
           "artist_name": "Led Zeppelin"
        },
        "user_id": 1,
        "listened_at": "1400000100",
        "user_name": "test",
        "recording_msid": "4269ddbc-9241-46da-935d-4fa9e0f7f371"
    }
    """,
    """
    {
        "track_metadata": {
           "track_name": "Immigrant Song 150",
           "additional_info": {
              "recording_mbid": "2cfad207-3f55-4aec-8120-86cf66e34d59",
              "artist_msid": "e229c8fa-7450-4916-8848-4535a40dc151",
              "release_msid": null
           },
           "artist_name": "Led Zeppelin"
        },
        "user_id": 1,
        "listened_at": "1400000150",
        "user_name": "test",
        "recording_msid": "4269ddbc-9241-46da-935d-4fa9e0f7f371"
    }
    """,
    """
    {
        "track_metadata": {
           "track_name": "Immigrant Song 200",
           "additional_info": {
              "recording_mbid": "2cfad207-3f55-4aec-8120-86cf66e34d59",
              "artist_msid": "e229c8fa-7450-4916-8848-4535a40dc151",
              "release_msid": null
           },
           "artist_name": "Led Zeppelin"
        },
        "user_id": 1,
        "listened_at": "1400000200",
        "user_name": "test",
        "recording_msid": "4269ddbc-9241-46da-935d-4fa9e0f7f371"
    }
    """
]

class TestInfluxListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestInfluxListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = init_influx_connection({ 'REDIS_HOST' : config.REDIS_HOST,
                                                 'INFLUX_HOST': config.INFLUX_HOST,
                                                 'INFLUX_PORT': config.INFLUX_PORT,
                                                 'INFLUX_DB': config.INFLUX_TEST_DB} )
        self.testuser_id = db.user.create("test")
        user = db.user.get(self.testuser_id)
        print(user)
        self.testuser_name = db.user.get(self.testuser_id)['musicbrainz_id']

    def tearDown(self):
        self.logstore = None
        super(TestInfluxListenStore, self).tearDown()

    def _create_test_data(self):
        test_data = [ Listen().from_json(ujson.loads(jdata)) for jdata in TEST_LISTEN_JSON ]
        self.logstore.insert(test_data)
        return len(test_data)

    def test_insert_influx(self):
        count = self._create_test_data()
        self.assertEquals(len(self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1399999999)), count)

    def test_fetch_listens_0(self):
        count = self._create_test_data()
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000000, limit=1)
        self.assertEquals(len(listens), 1)
        self.assertEquals(listens[0].ts_since_epoch, 1400000050)

    def test_fetch_listens_1(self):
        count = self._create_test_data()
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000000)
        self.assertEquals(len(listens), 4)
        self.assertEquals(listens[0].ts_since_epoch, 1400000200)
        self.assertEquals(listens[1].ts_since_epoch, 1400000150)
        self.assertEquals(listens[2].ts_since_epoch, 1400000100)
        self.assertEquals(listens[3].ts_since_epoch, 1400000050)

    def test_fetch_listens_2(self):
        count = self._create_test_data()
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000100)
        self.assertEquals(len(listens), 2)
        self.assertEquals(listens[0].ts_since_epoch, 1400000200)
        self.assertEquals(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_listens_3(self):
        count = self._create_test_data()
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
        self.assertEquals(len(listens), 5)
        self.assertEquals(listens[0].ts_since_epoch, 1400000200)
        self.assertEquals(listens[1].ts_since_epoch, 1400000150)
        self.assertEquals(listens[2].ts_since_epoch, 1400000100)
        self.assertEquals(listens[3].ts_since_epoch, 1400000050)
        self.assertEquals(listens[4].ts_since_epoch, 1400000000)
