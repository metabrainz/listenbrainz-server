# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from db.testing import DatabaseTestCase
import logging
from datetime import datetime
from .util import generate_data, to_epoch
from listenstore.listenstore import RedisListenStore, MIN_ID
from webserver.redis_connection import init_redis_connection
import random
import ujson


class TestRedisListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestRedisListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self._redis = init_redis_connection(self.config.TEST_SQLALCHEMY_DATABASE_URI)
        self._create_test_data()

    def tearDown(self):
        # self.logstore.drop_schema()
        self.logstore = None

    def _create_test_data(self):
        self.log.info("Inserting test data...")
        listen = generate_data(datetime.utcfromtimestamp(random.randint(MIN_ID, MIN_ID + 10000000)), 1)[0]
        listen = listen.__dict__
        p = self._redis.redis.pipeline()
        p.setex('playing_now' + ':' + listen['user_id'],
                ujson.dumps(listen).encode('utf-8'), self.config.PLAYING_NOW_MAX_DURATION)
        self.log.info("Test data inserted")

    def test_get_playing_now(self):
        playing_now = self._redis.get_playing_now("test")
        self.assertEquals(listen.__dict__, playing_now.__dict__)
