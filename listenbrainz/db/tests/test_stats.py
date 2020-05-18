# -*- coding: utf-8 -*-
import json
import os
import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user

from datetime import datetime, timezone
from listenbrainz.db.testing import DatabaseTestCase


class StatsDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'stats_user')

    def test_insert_user_stats(self):

        with open(self.path_to_data_file('user_top_artists.json')) as f:
            artists_data = json.load(f)
        with open(self.path_to_data_file('user_top_releases.json')) as f:
            releases = json.load(f)
        with open(self.path_to_data_file('user_top_recordings.json')) as f:
            recordings = json.load(f)

        db_stats.insert_user_stats(
            user_id=self.user['id'],
            artists=artists_data,
            recordings=recordings,
            releases=releases,
        )

        result = db_stats.get_all_user_stats(user_id=self.user['id'])
        self.assertListEqual(result['artist']['all_time']['artists'], artists_data['artists'])
        self.assertEqual(result['artist']['all_time']['count'], 2)
        self.assertListEqual(result['release']['all_time']['releases'], releases)
        self.assertListEqual(result['recording']['all_time']['recordings'], recordings)
        self.assertGreater(int(result['last_updated'].strftime('%s')), 0)

    def insert_test_data(self):
        """ Insert test data into the database """

        with open(self.path_to_data_file('user_top_artists.json')) as f:
            artists = json.load(f)
        with open(self.path_to_data_file('user_top_releases.json')) as f:
            releases = json.load(f)
        with open(self.path_to_data_file('user_top_recordings.json')) as f:
            recordings = json.load(f)

        db_stats.insert_user_stats(
            user_id=self.user['id'],
            artists=artists,
            recordings=recordings,
            releases=releases,
        )

        return {
            'user_artists': artists,
            'user_releases': releases,
            'user_recordings': recordings,
        }

    def test_get_timestamp_for_last_user_stats_update(self):
        ts = datetime.now(timezone.utc)
        self.insert_test_data()
        received_ts = db_stats.get_timestamp_for_last_user_stats_update()
        self.assertGreaterEqual(received_ts, ts)

    def test_get_user_stats(self):
        data_inserted = self.insert_test_data()

        data = db_stats.get_user_stats(self.user['id'], 'artist')
        self.assertEqual(data['artist']['all_time']['count'], 2)

        data = db_stats.get_user_stats(self.user['id'], 'recording')
        self.assertListEqual(data['recording']['all_time']['recordings'], data_inserted['user_recordings'])

    def test_get_user_artists(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_all_user_stats(self.user['id'])
        self.assertListEqual(result['artist']['all_time']['artists'], data_inserted['user_artists']['artists'])
        self.assertEqual(result['artist']['all_time']['count'], 2)
        self.assertEqual(result['artist']['all_time']['from'], 0)
        self.assertEqual(result['artist']['all_time']['to'], 10)

    def test_get_all_user_stats(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_all_user_stats(self.user['id'])
        self.assertListEqual(result['artist']['all_time']['artists'], data_inserted['user_artists']['artists'])
        self.assertEqual(result['artist']['all_time']['count'], 2)
        self.assertEqual(result['artist']['all_time']['from'], 0)
        self.assertEqual(result['artist']['all_time']['to'], 10)
        self.assertListEqual(result['release']['all_time']['releases'], data_inserted['user_releases'])
        self.assertListEqual(result['recording']['all_time']['recordings'], data_inserted['user_recordings'])
        self.assertGreater(int(result['last_updated'].strftime('%s')), 0)

    def test_valid_stats_exist(self):
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
        self.insert_test_data()
        self.assertTrue(db_stats.valid_stats_exist(self.user['id'], 7))

    def test_delete_user_stats(self):
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
        self.insert_test_data()
        data = db_stats.delete_user_stats(self.user['id'])
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
