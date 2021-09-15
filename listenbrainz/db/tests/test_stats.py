import json
import os
from datetime import datetime, timezone

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from data.model.common_stat import StatRange
from data.model.sitewide_artist_stat import SitewideArtistStatJson
from data.model.user_artist_map import UserArtistMapRecordList
from data.model.user_daily_activity import UserDailyActivityRecordList
from data.model.user_entity import UserEntityRecordList
from data.model.user_listening_activity import UserListeningActivityRecordList
from listenbrainz.db.testing import DatabaseTestCase


class StatsDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'stats_user')

    def test_insert_user_artists(self):
        """ Test if artist stats are inserted correctly """
        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = json.load(f)

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='artists',
                                        stats=StatRange[UserEntityRecordList](**artists_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='artists')
        self.assertDictEqual(result.dict(), artists_data)

    def test_insert_user_releases(self):
        """ Test if release stats are inserted correctly """
        with open(self.path_to_data_file('user_top_releases_db.json')) as f:
            releases_data = json.load(f)
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='releases',
                                        stats=StatRange[UserEntityRecordList](**releases_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='releases')
        self.assertDictEqual(result.dict(), releases_data)

    def test_insert_user_recordings(self):
        """ Test if recording stats are inserted correctly """
        with open(self.path_to_data_file('user_top_recordings_db.json')) as f:
            recordings_data = json.load(f)
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='recordings',
                                        stats=StatRange[UserEntityRecordList](**recordings_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='recordings')
        self.assertDictEqual(result.dict(), recordings_data)

    def test_insert_user_listening_activity(self):
        """ Test if listening activity stats are inserted correctly """
        with open(self.path_to_data_file('user_listening_activity_db.json')) as f:
            listening_activity_data = json.load(f)
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='listening_activity',
            stats=StatRange[UserListeningActivityRecordList](**listening_activity_data)
        )

    def test_insert_user_daily_activity(self):
        """ Test if daily activity stats are inserted correctly """
        with open(self.path_to_data_file('user_daily_activity_db.json')) as f:
            daily_activity_data = json.load(f)
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='daily_activity',
            stats=StatRange[UserDailyActivityRecordList](**daily_activity_data)
        )

        result = db_stats.get_user_daily_activity(user_id=self.user['id'], stats_range='all_time')
        self.assertDictEqual(result.dict(), daily_activity_data)

    def test_insert_user_artist_map(self):
        """ Test if daily activity stats are inserted correctly """
        with open(self.path_to_data_file('user_artist_map_db.json')) as f:
            artist_map_data = json.load(f)
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='artist_map',
            stats=StatRange[UserArtistMapRecordList](**artist_map_data)
        )

        result = db_stats.get_user_artist_map(user_id=self.user['id'], stats_range='all_time')
        self.assertDictEqual(result.dict(), artist_map_data)

    def test_insert_user_stats_mult_ranges_artist(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = json.load(f)

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='artists',
                                        stats=StatRange[UserEntityRecordList](**artists_data))
        artists_data['stats_range'] = 'year'
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='artists',
                                        stats=StatRange[UserEntityRecordList](**artists_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='artists')
        self.assertDictEqual(result.dict(), artists_data)

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='year', stats_type='artists')
        self.assertDictEqual(result.dict(), artists_data)

    def test_insert_user_stats_mult_ranges_release(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_releases_db.json')) as f:
            releases_data = json.load(f)

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='releases',
                                        stats=StatRange[UserEntityRecordList](**releases_data))
        releases_data['stats_range'] = 'year'
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='releases',
                                        stats=StatRange[UserEntityRecordList](**releases_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='releases')
        self.assertDictEqual(result.dict(), releases_data)

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='year', stats_type='releases')
        self.assertDictEqual(result.dict(), releases_data)

    def test_insert_user_stats_mult_ranges_recording(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_recordings_db.json')) as f:
            recordings_data = json.load(f)

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='recordings',
                                        stats=StatRange[UserEntityRecordList](**recordings_data))
        recordings_data['stats_range'] = 'year'
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='recordings',
                                        stats=StatRange[UserEntityRecordList](**recordings_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='recordings')
        self.assertDictEqual(result.dict(), recordings_data)

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='year', stats_type='recordings')
        self.assertDictEqual(result.dict(), recordings_data)

    def test_insert_user_stats_mult_ranges_listening_activity(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_listening_activity_db.json')) as f:
            listening_activity_data = json.load(f)

        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='listening_activity',
            stats=StatRange[UserListeningActivityRecordList](**listening_activity_data)
        )
        listening_activity_data['stat_range'] = 'year'
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='listening_activity',
            stats=StatRange[UserListeningActivityRecordList](**listening_activity_data)
        )

        result = db_stats.get_user_listening_activity(1, 'all_time')
        self.assertDictEqual(result.data.dict(), listening_activity_data)

        result = db_stats.get_user_listening_activity(1, 'year')
        self.assertDictEqual(result.data.dict(), listening_activity_data)

    def test_insert_user_stats_mult_ranges_daily_activity(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_daily_activity_db.json')) as f:
            daily_activity_data = json.load(f)

        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='daily_activity',
            stats=StatRange[UserDailyActivityRecordList](**daily_activity_data)
        )
        daily_activity_data['stat_range'] = 'year'
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='daily_activity',
            stats=StatRange[UserDailyActivityRecordList](**daily_activity_data)
        )

        result = db_stats.get_user_daily_activity(1, 'all_time')
        self.assertDictEqual(result.data.dict(), daily_activity_data)

        result = db_stats.get_user_daily_activity(1, 'year')
        self.assertDictEqual(result.data.dict(), daily_activity_data)

    def test_insert_user_stats_mult_ranges_artist_map(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_artist_map_db.json')) as f:
            artist_map_data = json.load(f)

        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='artist_map',
            stats=StatRange[UserArtistMapRecordList](**artist_map_data)
        )
        artist_map_data['stat_range'] = 'year'
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='artist_map',
            stats=StatRange[UserArtistMapRecordList](**artist_map_data)
        )

        result = db_stats.get_user_artist_map(1, 'all_time')
        self.assertDictEqual(result.data.dict(), artist_map_data)

        result = db_stats.get_user_artist_map(1, 'year')
        self.assertDictEqual(result.data.dict(), artist_map_data)

    def test_insert_sitewide_artists(self):
        """ Test if sitewide artist data is inserted correctly """
        with open(self.path_to_data_file('sitewide_top_artists_db.json')) as f:
            artists_data = json.load(f)

        db_stats.insert_sitewide_artists(stats_range='all_time', artists=SitewideArtistStatJson(**artists_data))

        result = db_stats.get_sitewide_artists('all_time')
        self.assertDictEqual(result.data.dict(), artists_data)

    def insert_test_data(self):
        """ Insert test data into the database """

        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            user_artists = json.load(f)
        with open(self.path_to_data_file('user_top_releases_db.json')) as f:
            releases = json.load(f)
        with open(self.path_to_data_file('user_top_recordings_db.json')) as f:
            recordings = json.load(f)
        with open(self.path_to_data_file('user_listening_activity_db.json')) as f:
            listening_activity = json.load(f)
        with open(self.path_to_data_file('user_daily_activity_db.json')) as f:
            daily_activity = json.load(f)
        with open(self.path_to_data_file('user_artist_map_db.json')) as f:
            artist_map = json.load(f)
        with open(self.path_to_data_file('sitewide_top_artists_db.json')) as f:
            sitewide_artists = json.load(f)

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='artists',
                                        stats=StatRange[UserEntityRecordList](**user_artists))
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='releases',
                                        stats=StatRange[UserEntityRecordList](**releases))
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='recordings',
                                        stats=StatRange[UserEntityRecordList](**recordings))
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='listening_activity',
            stats=StatRange[UserListeningActivityRecordList](**listening_activity)
        )
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='daily_activity',
            stats=StatRange[UserDailyActivityRecordList](**daily_activity)
        )
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='artist_map',
            stats=StatRange[UserArtistMapRecordList](**artist_map)
        )
        db_stats.insert_sitewide_artists('all_time', SitewideArtistStatJson(**sitewide_artists))

        return {
            'user_artists': user_artists,
            'user_releases': releases,
            'user_recordings': recordings,
            'user_listening_activity': listening_activity,
            'user_daily_activity': daily_activity,
            'user_artist_map': artist_map,
            'sitewide_artists': sitewide_artists
        }

    def test_get_timestamp_for_last_user_stats_update(self):
        ts = datetime.now(timezone.utc)
        self.insert_test_data()
        received_ts = db_stats.get_timestamp_for_last_user_stats_update()
        self.assertGreaterEqual(received_ts, ts)

    def test_get_user_artists(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_stats(self.user['id'], 'all_time', 'artists')
        self.assertDictEqual(result.data.dict(), data_inserted['user_artists'])

    def test_get_user_releases(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_stats(self.user['id'], 'all_time', 'releases')
        self.assertDictEqual(result.data.dict(), data_inserted['user_releases'])

    def test_get_user_recordings(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_stats(self.user['id'], 'all_time', 'recordings')
        self.assertDictEqual(result.data.dict(), data_inserted['user_recordings'])

    def test_get_user_listening_activity(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_listening_activity(self.user['id'], 'all_time')
        self.assertDictEqual(result.data.dict(), data_inserted['user_listening_activity'])

    def test_get_user_daily_activity(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_daily_activity(self.user['id'], 'all_time')
        self.assertDictEqual(result.data.dict(), data_inserted['user_daily_activity'])

    def test_get_user_artist_map(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_artist_map(self.user['id'], 'all_time')
        self.assertDictEqual(result.data.dict(), data_inserted['user_artist_map'])

    def test_get_sitewide_artists(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_sitewide_artists('all_time')
        self.assertDictEqual(result.data.dict(), data_inserted['sitewide_artists'])

    def test_valid_stats_exist(self):
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
        self.insert_test_data()
        self.assertTrue(db_stats.valid_stats_exist(self.user['id'], 7))

    def test_delete_user_stats(self):
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
        self.insert_test_data()
        db_stats.delete_user_stats(self.user['id'])
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
