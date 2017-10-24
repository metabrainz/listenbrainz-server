# -*- coding: utf-8 -*-
import json
import os
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats
from listenbrainz.db.testing import DatabaseTestCase


class StatsDatabaseTestCase(DatabaseTestCase):

    TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'testdata')

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create('stats_user')


    def test_insert_user_stats(self):

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
            artist_count=2,
        )

        result = db_stats.get_user_stats(user_id=self.user['id'])
        self.assertDictEqual(result['artist']['all_time'], artists)
        self.assertEqual(result['artist']['count'], 2)
        self.assertDictEqual(result['release'], releases)
        self.assertDictEqual(result['recording'], recordings)
        self.assertGreater(int(result['last_updated'].strftime('%s')), 0)

