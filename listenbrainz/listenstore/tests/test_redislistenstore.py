# coding=utf-8

import datetime
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


    def test_update_and_get_recent_listens(self):

        dt0 = datetime.datetime.now()
        dt1 = dt0.replace(second=(dt0.second + 1) % 60)

        recent = self._redis.get_recent_listens()
        self.assertEqual(recent, [])

        listens = []
        listens.append({
            'user_id': self.testuser['id'],
            'user_name': self.testuser['musicbrainz_id'],
            'listened_at': dt0,
            'track_metadata': {
                'artist_name': 'The Dimwitted Hillbillies',
                'track_name': 'Ice cream, guns and bling!',
                'additional_info': {},
            },
        })
        listens.append({
            'user_id': self.testuser['id'],
            'user_name': self.testuser['musicbrainz_id'],
            'listened_at': dt1,
            'track_metadata': {
                'artist_name': 'The Dimwitted Hillbillies',
                'track_name': 'White gas and sparklers are a great combo for toddlers!',
                'additional_info': {},
            },
        })
        self._redis.update_recent_listens(listens)

        recent = self._redis.get_recent_listens()
        self.assertEqual(len(recent), 2)
        self.assertIsInstance(recent[0], Listen)
        self.assertEqual(recent[0].timestamp, dt1)
        self.assertEqual(recent[1].timestamp, dt0)

        recent = self._redis.get_recent_listens(1)
        self.assertEqual(len(recent), 1)
