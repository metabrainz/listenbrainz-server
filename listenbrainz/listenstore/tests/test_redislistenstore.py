# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from listenbrainz.db.testing import DatabaseTestCase
import logging
from datetime import datetime
from listenbrainz.listenstore.tests.util import generate_data, to_epoch
from listenbrainz.listenstore import MIN_ID, RedisListenStore
from listenbrainz.webserver.redis_connection import init_redis_connection
from redis.connection import Connection
import random
import ujson
import listenbrainz.db.user as db_user


class TestRedisListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestRedisListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self._redis = init_redis_connection(self.log, self.config.REDIS_HOST, self.config.REDIS_PORT)
        self.testuser_id = db_user.create("test")
        self._create_test_data()

    def tearDown(self):
        self._redis.redis.flushdb()
        Connection(self._redis.redis).disconnect()
        super(TestRedisListenStore, self).tearDown()

    def _create_test_data(self):
        self.log.info("Inserting test data...")
        self.listen = generate_data(self.testuser_id, MIN_ID + 1, 1)[0]
        listen = self.listen.to_json()
        self._redis.redis.setex('playing_now' + ':' + str(listen['user_id']),
                                ujson.dumps(listen).encode('utf-8'), self.config.PLAYING_NOW_MAX_DURATION)
        self.log.info("Test data inserted")

    def test_get_playing_now(self):
        playing_now = self._redis.get_playing_now(self.listen.user_id)
        assert playing_now is not None
