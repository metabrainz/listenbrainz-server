import json
from copy import deepcopy
from datetime import datetime, timezone

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from data.model.common_stat import StatRange
from data.model.user_artist_map import UserArtistMapRecord
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz.db.testing import DatabaseTestCase


class StatsDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'stats_user')
        self.create_user_with_id(db_stats.SITEWIDE_STATS_USER_ID, 2, "listenbrainz-stats-user")
        self.maxDiff = None

    def test_insert_user_artists(self):
        """ Test if artist stats are inserted correctly """
        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = json.load(f)

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='artists',
                                        stats=StatRange[EntityRecord](**artists_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='artists')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), artists_data)

    def test_insert_user_releases(self):
        """ Test if release stats are inserted correctly """
        with open(self.path_to_data_file('user_top_releases_db.json')) as f:
            releases_data = json.load(f)
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='releases',
                                        stats=StatRange[EntityRecord](**releases_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='releases')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), releases_data)

    def test_insert_user_recordings(self):
        """ Test if recording stats are inserted correctly """
        with open(self.path_to_data_file('user_top_recordings_db.json')) as f:
            recordings_data = json.load(f)
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='recordings',
                                        stats=StatRange[EntityRecord](**recordings_data))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='recordings')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), recordings_data)

    def test_insert_user_listening_activity(self):
        """ Test if listening activity stats are inserted correctly """
        with open(self.path_to_data_file('user_listening_activity_db.json')) as f:
            listening_activity_data = json.load(f)
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='listening_activity',
            stats=StatRange[ListeningActivityRecord](**listening_activity_data)
        )

    def test_insert_user_daily_activity(self):
        """ Test if daily activity stats are inserted correctly """
        with open(self.path_to_data_file('user_daily_activity_db.json')) as f:
            daily_activity_data = json.load(f)
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='daily_activity',
            stats=StatRange[DailyActivityRecord](**daily_activity_data)
        )

        result = db_stats.get_user_daily_activity(user_id=self.user['id'], stats_range='all_time')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), daily_activity_data)

    def test_insert_user_artist_map(self):
        """ Test if daily activity stats are inserted correctly """
        with open(self.path_to_data_file('user_artist_map_db.json')) as f:
            artist_map_data = json.load(f)
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='artist_map',
            stats=StatRange[UserArtistMapRecord](**artist_map_data)
        )

        result = db_stats.get_user_artist_map(user_id=self.user['id'], stats_range='all_time')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), artist_map_data)

    def test_insert_user_stats_mult_ranges_artist(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = json.load(f)
        artists_data_year = deepcopy(artists_data)
        artists_data_year['stats_range'] = 'year'

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='artists',
                                        stats=StatRange[EntityRecord](**artists_data))
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='artists',
                                        stats=StatRange[EntityRecord](**artists_data_year))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='artists')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), artists_data)

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='year', stats_type='artists')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), artists_data_year)

    def test_insert_user_stats_mult_ranges_release(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_releases_db.json')) as f:
            releases_data = json.load(f)
        releases_data_year = deepcopy(releases_data)
        releases_data_year['stats_range'] = 'year'

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='releases',
                                        stats=StatRange[EntityRecord](**releases_data))
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='releases',
                                        stats=StatRange[EntityRecord](**releases_data_year))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='releases')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), releases_data)

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='year', stats_type='releases')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), releases_data_year)

    def test_insert_user_stats_mult_ranges_recording(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_top_recordings_db.json')) as f:
            recordings_data = json.load(f)
        recordings_data_year = deepcopy(recordings_data)
        recordings_data_year['stats_range'] = 'year'

        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='recordings',
                                        stats=StatRange[EntityRecord](**recordings_data))
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='recordings',
                                        stats=StatRange[EntityRecord](**recordings_data_year))

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='all_time', stats_type='recordings')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), recordings_data)

        result = db_stats.get_user_stats(user_id=self.user['id'], stats_range='year', stats_type='recordings')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), recordings_data_year)

    def test_insert_user_stats_mult_ranges_listening_activity(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_listening_activity_db.json')) as f:
            listening_activity_data = json.load(f)
        listening_activity_data_year = deepcopy(listening_activity_data)
        listening_activity_data_year['stats_range'] = 'year'

        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='listening_activity',
            stats=StatRange[ListeningActivityRecord](**listening_activity_data)
        )
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='listening_activity',
            stats=StatRange[ListeningActivityRecord](**listening_activity_data_year)
        )

        result = db_stats.get_user_listening_activity(1, 'all_time')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), listening_activity_data)

        result = db_stats.get_user_listening_activity(1, 'year')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), listening_activity_data_year)

    def test_insert_user_stats_mult_ranges_daily_activity(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_daily_activity_db.json')) as f:
            daily_activity_data = json.load(f)
        daily_activity_data_year = deepcopy(daily_activity_data)
        daily_activity_data_year['stats_range'] = 'year'

        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='daily_activity',
            stats=StatRange[DailyActivityRecord](**daily_activity_data)
        )
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='daily_activity',
            stats=StatRange[DailyActivityRecord](**daily_activity_data_year)
        )

        result = db_stats.get_user_daily_activity(1, 'all_time')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), daily_activity_data)

        result = db_stats.get_user_daily_activity(1, 'year')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), daily_activity_data_year)

    def test_insert_user_stats_mult_ranges_artist_map(self):
        """ Test if multiple time range data is inserted correctly """
        with open(self.path_to_data_file('user_artist_map_db.json')) as f:
            artist_map_data = json.load(f)
        artist_map_data_year = deepcopy(artist_map_data)
        artist_map_data_year['stats_range'] = 'year'

        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='artist_map',
            stats=StatRange[UserArtistMapRecord](**artist_map_data)
        )
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='artist_map',
            stats=StatRange[UserArtistMapRecord](**artist_map_data_year)
        )

        result = db_stats.get_user_artist_map(1, 'all_time')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), artist_map_data)

        result = db_stats.get_user_artist_map(1, 'year')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), artist_map_data_year)

    def test_insert_sitewide_artists(self):
        """ Test if sitewide artist data is inserted correctly """
        with open(self.path_to_data_file('sitewide_top_artists_db.json')) as f:
            artists_data = json.load(f)

        db_stats.insert_sitewide_jsonb_data('artists', StatRange[EntityRecord](**artists_data))

        result = db_stats.get_sitewide_stats('all_time', 'artists')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), artists_data)

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
                                        stats=StatRange[EntityRecord](**user_artists))
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='releases',
                                        stats=StatRange[EntityRecord](**releases))
        db_stats.insert_user_jsonb_data(user_id=self.user['id'], stats_type='recordings',
                                        stats=StatRange[EntityRecord](**recordings))
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='listening_activity',
            stats=StatRange[ListeningActivityRecord](**listening_activity)
        )
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='daily_activity',
            stats=StatRange[DailyActivityRecord](**daily_activity)
        )
        db_stats.insert_user_jsonb_data(
            user_id=self.user['id'], stats_type='artist_map',
            stats=StatRange[UserArtistMapRecord](**artist_map)
        )
        db_stats.insert_sitewide_jsonb_data('artists', StatRange[EntityRecord](**sitewide_artists))

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
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['user_artists'])

    def test_get_user_releases(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_stats(self.user['id'], 'all_time', 'releases')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['user_releases'])

    def test_get_user_recordings(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_stats(self.user['id'], 'all_time', 'recordings')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['user_recordings'])

    def test_get_user_listening_activity(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_listening_activity(self.user['id'], 'all_time')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), data_inserted['user_listening_activity'])

    def test_get_user_daily_activity(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_daily_activity(self.user['id'], 'all_time')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), data_inserted['user_daily_activity'])

    def test_get_user_artist_map(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_user_artist_map(self.user['id'], 'all_time')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), data_inserted['user_artist_map'])

    def test_get_sitewide_artists(self):
        data_inserted = self.insert_test_data()
        result = db_stats.get_sitewide_stats('all_time', 'artists')
        self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['sitewide_artists'])

    def test_valid_stats_exist(self):
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
        self.insert_test_data()
        self.assertTrue(db_stats.valid_stats_exist(self.user['id'], 7))

    def test_delete_user_stats(self):
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
        self.insert_test_data()
        db_stats.delete_user_stats(self.user['id'])
        self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
