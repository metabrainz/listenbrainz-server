# coding=utf-8

import logging
import time
import ujson

from redis.connection import Connection

import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listen import Listen
from listenbrainz.listenstore.tests.util import generate_data
from listenbrainz.webserver.redis_connection import init_redis_connection


class RedisListenStoreTestCase(DatabaseTestCase):

    def setUp(self):
        super(RedisListenStoreTestCase, self).setUp()
        self.log = logging.getLogger()
        self._redis = init_redis_connection(self.log, self.config.REDIS_HOST, self.config.REDIS_PORT)
        self.testuser = db_user.get_or_create(1, "test")

    def tearDown(self):
        self._redis.redis.flushdb()
        Connection(self._redis.redis).disconnect()
        super(RedisListenStoreTestCase, self).tearDown()

    def test_get_and_put_playing_now(self):
        listen = {
            'user_id': self.testuser['id'],
            'user_name': self.testuser['musicbrainz_id'],
            'listened_at': int(time.time()),
            'track_metadata': {
                'artist_name': 'The Strokes',
                'track_name': 'Call It Fate, Call It Karma',
                'additional_info': {},
            },
        }
        self._redis.put_playing_now(listen['user_id'], listen, self.config.PLAYING_NOW_MAX_DURATION)

        playing_now = self._redis.get_playing_now(listen['user_id'])
        self.assertIsNotNone(playing_now)
        self.assertIsInstance(playing_now, Listen)
        self.assertEqual(playing_now.data['artist_name'], 'The Strokes')
        self.assertEqual(playing_now.data['track_name'], 'Call It Fate, Call It Karma')
