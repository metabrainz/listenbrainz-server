import logging
import unittest
from copy import deepcopy
from unittest.mock import patch

from flask import Flask

from listenbrainz.listenstore.redis_listenstore import RedisListenStore
from listenbrainz.webserver.views import api_tools


class PlayingNowExpiryTestCase(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config['PLAYING_NOW_MAX_DURATION'] = 600
        self.enterContext(app.app_context())
        self.now = 0
        self.entries = {}
        self.enterContext(patch('brainzutils.cache.get', side_effect=self.cache_get))
        self.enterContext(patch('brainzutils.cache.set', side_effect=self.cache_set))
        self.store = RedisListenStore(logging.getLogger(__name__))
        self.enterContext(patch.object(api_tools.redis_connection, '_redis', self.store))
        self.publish = self.enterContext(patch.object(api_tools, 'publish_data_to_queue'))
        self.listen = {
            'user_id': 1,
            'user_name': 'test',
            'track_metadata': {
                'artist_name': 'Artist',
                'track_name': 'Track',
                'additional_info': {},
            },
        }

    def cache_get(self, key):
        entry = self.entries.get(key)
        if entry is not None and self.now < entry[1]:
            return entry[0]
        return None

    def cache_set(self, key, value, expirein):
        self.entries[key] = (value, self.now + expirein)

    def submit(self):
        api_tools._send_listens_to_queue(api_tools.LISTEN_TYPE_PLAYING_NOW, [self.listen])

    def test_repeat_refreshes_expiry_without_duplicate_broadcast(self):
        for additional_info, duration in [
            ({'duration': 329}, 329),
            ({'duration_ms': 329387}, 329),
            ({}, 600),
        ]:
            with self.subTest(additional_info=additional_info):
                self.entries.clear()
                self.now = 0
                self.publish.reset_mock()
                self.listen['track_metadata']['additional_info'] = additional_info
                self.submit()

                # A faster request for the next play arrives before the old TTL.
                self.now = duration - 1
                self.submit()
                self.assertEqual(self.publish.call_count, 1)

                self.now = duration
                self.assertIsNotNone(self.store.get_playing_now(1))
                self.now = 2 * duration - 1
                self.assertIsNone(self.store.get_playing_now(1))

    def test_different_artist_or_track_is_broadcast(self):
        for field in ('artist_name', 'track_name'):
            with self.subTest(field=field):
                self.entries.clear()
                self.publish.reset_mock()
                self.submit()
                changed = deepcopy(self.listen)
                changed['track_metadata'][field] += ' changed'
                api_tools._send_listens_to_queue(api_tools.LISTEN_TYPE_PLAYING_NOW, [changed])
                self.assertEqual(self.publish.call_count, 2)
                self.assertEqual(self.store.get_playing_now(1).data[field], changed['track_metadata'][field])

    def test_repeat_after_expiry_is_broadcast(self):
        self.submit()
        self.now = 600
        self.submit()
        self.assertEqual(self.publish.call_count, 2)
        self.assertIsNotNone(self.store.get_playing_now(1))
