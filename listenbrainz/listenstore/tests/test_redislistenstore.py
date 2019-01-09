# coding=utf-8

import logging
import ujson

from redis.connection import Connection

import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listenstore.tests.util import generate_data
from listenbrainz.webserver.redis_connection import init_redis_connection


class TestRedisListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestRedisListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self._redis = init_redis_connection(self.log, self.config.REDIS_HOST, self.config.REDIS_PORT)
        self.testuser_id = db_user.create(1, "test")
        self._create_test_data()

    def tearDown(self):
        self._redis.redis.flushdb()
        Connection(self._redis.redis).disconnect()
        super(TestRedisListenStore, self).tearDown()

    def _create_test_data(self):
        self.log.info("Inserting test data...")
        self.listen = generate_data(self.testuser_id,'test', None , 1)[0]
        listen = self.listen.to_json()
        self._redis.redis.setex('playing_now' + ':' + str(listen['user_id']),
                                ujson.dumps(listen).encode('utf-8'), self.config.PLAYING_NOW_MAX_DURATION)
        self.log.info("Test data inserted")

    def test_get_playing_now(self):
        playing_now = self._redis.get_playing_now(self.listen.user_id)
        assert playing_now is not None
