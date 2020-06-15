import json
import os
import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user

from datetime import datetime, timezone
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.model.user_artist_stat import UserArtistStatJson
from listenbrainz.db.model.user_release_stat import UserReleaseStatJson
from listenbrainz.db.model.user_recording_stat import UserRecordingStatJson


class StatsDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'stats_user')

    def test_insert_user_artists(self):
        """ Test if artist stats are inserted correctly """
        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = json.load(f)

        db_stats.insert_user_artists(user_id=self.user['id'], artists=UserArtistStatJson(**{'all_time': artists_data}))

        result = db_stats.get_user_artists(user_id=self.user['id'], stats_range='all_time')
        self.assertDictEqual(result.all_time.dict(), artists_data)

    def test_insert_user_releases(self):
        """ Test if release stats are inserted correctly """
        with open(self.path_to_data_file('user_top_releases_db.json')) as f:
            releases_data = json.load(f)
        db_stats.insert_user_releases(user_id=self.user['id'], releases=UserReleaseStatJson(**{'all_time': releases_data}))

        result = db_stats.get_user_releases(user_id=self.user['id'], stats_range='all_time')
        self.assertDictEqual(result.all_time.dict(), releases_data)

    def test_insert_user_recordings(self):
        """ Test if recording stats are inserted correctly """
        with open(self.path_to_data_file('user_top_recordings_db.json')) as f:
            recordings_data = json.load(f)
        db_stats.insert_user_recordings(user_id=self.user['id'],
                                        recordings=UserRecordingStatJson(**{'all_time': recordings_data}))

        result = db_stats.get_user_recordings(user_id=self.user['id'], stats_range='all_time')
        self.assertDictEqual(result.all_time.dict(), recordings_data)

    def test_insert_user_stats_mult_ranges_artist(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = json.load(f)

        db_stats.insert_user_artists(user_id=self.user['id'], artists=UserArtistStatJson(**{'all_time': artists_data}))
        db_stats.insert_user_artists(user_id=self.user['id'], artists=UserArtistStatJson(**{'year': artists_data}))

        result = db_stats.get_user_artists(1, 'all_time')
        self.assertDictEqual(result.all_time.dict(), artists_data)

        result = db_stats.get_user_artists(1, 'year')
        self.assertDictEqual(result.year.dict(), artists_data)

    def test_insert_user_stats_mult_ranges_release(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_releases_db.json')) as f:
            releases_data = json.load(f)

        db_stats.insert_user_releases(user_id=self.user['id'], releases=UserReleaseStatJson(**{'year': releases_data}))
        db_stats.insert_user_releases(user_id=self.user['id'], releases=UserReleaseStatJson(**{'all_time': releases_data}))

        result = db_stats.get_user_releases(1, 'all_time')
        self.assertDictEqual(result.all_time.dict(), releases_data)

        result = db_stats.get_user_releases(1, 'year')
        self.assertDictEqual(result.year.dict(), releases_data)

    def test_insert_user_stats_mult_ranges_recording(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_recordings_db.json')) as f:
            recordings_data = json.load(f)

        db_stats.insert_user_recordings(user_id=self.user['id'], recordings=UserRecordingStatJson(**{'year': recordings_data}))
        db_stats.insert_user_recordings(user_id=self.user['id'],
                                        recordings=UserRecordingStatJson(**{'all_time': recordings_data}))

        result = db_stats.get_user_recordings(1, 'all_time')
        self.assertDictEqual(result.all_time.dict(), recordings_data)

        result = db_stats.get_user_recordings(1, 'year')
        self.assertDictEqual(result.year.dict(), recordings_data)

    def insert_test_data(self):
        """ Insert test data into the database """

        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists = json.load(f)
        with open(self.path_to_data_file('user_top_releases_db.json')) as f:
            releases = json.load(f)
        with open(self.path_to_data_file('user_top_recordings_db.json')) as f:
            recordings = json.load(f)

        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'all_time': artists}))
        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'all_time': releases}))
        db_stats.insert_user_recordings(self.user['id'], UserRecordingStatJson(**{'all_time': recordings}))

        return {
            'user_artists': artists,
            'user_releases': releases,
            'user_recordings': recordings
        }

    def test_get_timestamp_for_last_user_stats_update(self):
        ts = datetime.now(timezone.utc)
        self.insert_test_data()
        received_ts = db_stats.get_timestamp_for_last_user_stats_update()
        self.assertGreaterEqual(received_ts, ts)

    def test_get_user_artists(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_artists(self.user['id'], 'all_time')
        self.assertDictEqual(result.all_time.dict(), data_inserted['user_artists'])

    def test_get_user_releases(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_releases(self.user['id'], 'all_time')
        self.assertDictEqual(result.all_time.dict(), data_inserted['user_releases'])

    def test_get_user_recordings(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_recordings(self.user['id'], 'all_time')
        self.assertDictEqual(result.all_time.dict(), data_inserted['user_recordings'])

    def test_valid_stats_exist(self):
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
        self.insert_test_data()
        self.assertTrue(db_stats.valid_stats_exist(self.user['id'], 7))

    def test_delete_user_stats(self):
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
        self.insert_test_data()
        db_stats.delete_user_stats(self.user['id'])
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
