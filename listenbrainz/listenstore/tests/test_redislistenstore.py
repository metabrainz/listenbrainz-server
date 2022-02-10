# coding=utf-8

import datetime
import logging
import time
import uuid

from dateutil.relativedelta import relativedelta
from redis.connection import Connection

from brainzutils import cache
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz import config
from listenbrainz.listen import Listen, NowPlayingListen
from listenbrainz.utils import init_cache
from listenbrainz.webserver.redis_connection import init_redis_connection
from listenbrainz.listenstore.redis_listenstore import RedisListenStore


class RedisListenStoreTestCase(DatabaseTestCase):

    def setUp(self):
        super(RedisListenStoreTestCase, self).setUp()
        # TODO: Ideally this would use a config from a flask app, but this test case doesn't create an app
        init_cache(config.REDIS_HOST, config.REDIS_PORT, config.REDIS_NAMESPACE)

        self.log = logging.getLogger()
        self._redis = init_redis_connection(self.log)
        self.testuser = db_user.get_or_create(1, "test")

    def tearDown(self):
        cache._r.flushdb()
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
        self._redis.put_playing_now(listen['user_id'], listen, config.PLAYING_NOW_MAX_DURATION)

        playing_now = self._redis.get_playing_now(listen['user_id'])
        self.assertIsNotNone(playing_now)
        self.assertIsInstance(playing_now, NowPlayingListen)
        self.assertEqual(playing_now.data['artist_name'], 'The Strokes')
        self.assertEqual(playing_now.data['track_name'], 'Call It Fate, Call It Karma')


    def test_update_and_get_recent_listens(self):

        recent = self._redis.get_recent_listens()
        self.assertEqual(recent, [])

        listens = []
        t = int(time.time())
        for i in range(RedisListenStore.RECENT_LISTENS_MAX * 3):
            listen = Listen(user_id=self.testuser['id'],
                            user_name = self.testuser['musicbrainz_id'],
                            timestamp = t - i,
                            data = {
                                'artist_name': str(uuid.uuid4()),
                                'track_name': str(uuid.uuid4()),
                                'additional_info': {},
                            }
            )
            listens.append(listen)
            self._redis.update_recent_listens(listens)

        recent = self._redis.get_recent_listens()
        self.assertEqual(len(recent), RedisListenStore.RECENT_LISTENS_MAX)
        self.assertIsInstance(recent[0], Listen)
        for i, r in enumerate(recent):
            self.assertEqual(r.timestamp, listens[i].timestamp)

        recent = self._redis.get_recent_listens(5)
        self.assertEqual(len(recent), 5)
        for i, r in enumerate(recent):
            self.assertEqual(r.timestamp, listens[i].timestamp)

    def test_incr_listen_count_for_day(self):
        today = datetime.datetime.utcnow()
        # get without setting any value, should return None
        self.assertIsNone(self._redis.get_listen_count_for_day(today))

        # set a value to a key that doesn't exist
        self._redis.increment_listen_count_for_day(today, 2)
        self.assertEqual(2, self._redis.get_listen_count_for_day(today))

        # increment again
        self._redis.increment_listen_count_for_day(today, 3)
        self.assertEqual(5, self._redis.get_listen_count_for_day(today))

        # check for a different day
        yesterday = today - relativedelta(days=1)
        self.assertIsNone(self._redis.get_listen_count_for_day(yesterday))

        self._redis.increment_listen_count_for_day(yesterday, 2)
        self.assertEqual(2, self._redis.get_listen_count_for_day(yesterday))
