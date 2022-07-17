import itertools
import json
from copy import deepcopy
from datetime import datetime, timezone

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from data.model.common_stat import StatRange, StatApi, StatRecordList
from data.model.user_artist_map import UserArtistMapRecord
from data.model.user_artist_stat import ArtistRecord
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import couchdb
from listenbrainz.webserver import create_app


class StatsDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'stats_user')
        self.create_user_with_id(db_stats.SITEWIDE_STATS_USER_ID, 2, "listenbrainz-stats-user")
        self.maxDiff = None

    def _test_one_stat(self, entity, range_):
        with open(self.path_to_data_file(f'user_top_{entity}_db_data_for_api_test_{range_}.json')) as f:
            original = json.load(f)

        # insert_stats_in_couchdb modifies the data in place so make a copy first
        data = deepcopy(original)

        database1, database2 = f"{entity}_{range_}_20220716", f"{entity}_{range_}_20220717"
        from_ts1, to_ts1 = int(datetime(2022, 7, 9).timestamp()), int(datetime(2022, 7, 16).timestamp())
        from_ts2, to_ts2 = int(datetime(2022, 7, 10).timestamp()), int(datetime(2022, 7, 17).timestamp())

        couchdb.create_database(database1)
        db_stats.insert_stats_in_couchdb(database1, from_ts1, to_ts1, data)

        couchdb.create_database(database2)
        db_stats.insert_stats_in_couchdb(database2, from_ts2, to_ts2, data[:1])

        received = db_stats.get_stats_from_couchdb(1, entity, range_).dict()
        expected = original[0] | {
            "from_ts": from_ts2,
            "to_ts": to_ts2,
            "last_updated": received["last_updated"],
            "stats_range": range_
        }
        self.assertEqual(received, expected)

        received = db_stats.get_stats_from_couchdb(2, entity, range_).dict()
        expected = original[1] | {
            "from_ts": from_ts1,
            "to_ts": to_ts1,
            "last_updated": received["last_updated"],
            "stats_range": range_
        }
        self.assertEqual(received, expected)

    def test_user_stats(self):
        entities = ["artists", "releases", "recordings"]
        ranges = ["week", "month", "year"]

        with create_app().app_context():
            for (entity, range_) in itertools.product(entities, ranges):
                with self.subTest(f"{range_} {entity} user stats", entity=entity, range_=range_):
                    self._test_one_stat(entity, range_)

    # def test_insert_user_listening_activity(self):
    #     """ Test if listening activity stats are inserted correctly """
    #     with open(self.path_to_data_file('user_listening_activity_db.json')) as f:
    #         listening_activity_data = json.load(f)
    #     db_stats.insert_user_jsonb_data(
    #         user_id=self.user['id'], stats_type='listening_activity',
    #         stats=StatRange[ListeningActivityRecord](**listening_activity_data)
    #     )
    #
    # def test_insert_user_daily_activity(self):
    #     """ Test if daily activity stats are inserted correctly """
    #     with open(self.path_to_data_file('user_daily_activity_db.json')) as f:
    #         daily_activity_data = json.load(f)
    #     db_stats.insert_user_jsonb_data(
    #         user_id=self.user['id'], stats_type='daily_activity',
    #         stats=StatRange[DailyActivityRecord](**daily_activity_data)
    #     )
    #
    #     result = db_stats.get_user_daily_activity(user_id=self.user['id'], stats_range='all_time')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), daily_activity_data)
    #
    # def test_insert_user_artist_map(self):
    #     """ Test if daily activity stats are inserted correctly """
    #     with open(self.path_to_data_file('user_artist_map_db.json')) as f:
    #         artist_map_data = json.load(f)
    #     db_stats.insert_user_jsonb_data(
    #         user_id=self.user['id'], stats_type='artist_map',
    #         stats=StatRange[UserArtistMapRecord](**artist_map_data)
    #     )
    #
    #     result = db_stats.get_user_artist_map(user_id=self.user['id'], stats_range='all_time')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), artist_map_data)
    #
    #
    # def test_get_timestamp_for_last_user_stats_update(self):
    #     ts = datetime.now(timezone.utc)
    #     self.insert_test_data()
    #     received_ts = db_stats.get_timestamp_for_last_user_stats_update()
    #     self.assertGreaterEqual(received_ts, ts)
    #
    # def test_get_user_artists(self):
    #     data_inserted = self.insert_test_data()
    #     result = db_stats.get_user_stats(self.user['id'], 'all_time', 'artists')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['user_artists'])
    #
    # def test_get_user_releases(self):
    #     data_inserted = self.insert_test_data()
    #     result = db_stats.get_user_stats(self.user['id'], 'all_time', 'releases')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['user_releases'])
    #
    # def test_get_user_recordings(self):
    #     data_inserted = self.insert_test_data()
    #     result = db_stats.get_user_stats(self.user['id'], 'all_time', 'recordings')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['user_recordings'])
    #
    # def test_get_user_listening_activity(self):
    #     data_inserted = self.insert_test_data()
    #     result = db_stats.get_user_listening_activity(self.user['id'], 'all_time')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), data_inserted['user_listening_activity'])
    #
    # def test_get_user_daily_activity(self):
    #     data_inserted = self.insert_test_data()
    #     result = db_stats.get_user_daily_activity(self.user['id'], 'all_time')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), data_inserted['user_daily_activity'])
    #
    # def test_get_user_artist_map(self):
    #     data_inserted = self.insert_test_data()
    #     result = db_stats.get_user_artist_map(self.user['id'], 'all_time')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated', 'count'}), data_inserted['user_artist_map'])
    #
    # def test_get_sitewide_artists(self):
    #     data_inserted = self.insert_test_data()
    #     result = db_stats.get_sitewide_stats('all_time', 'artists')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['sitewide_artists'])
    #
    # def test_valid_stats_exist(self):
    #     self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
    #     self.insert_test_data()
    #     self.assertTrue(db_stats.valid_stats_exist(self.user['id'], 7))
    #
    # def test_delete_user_stats(self):
    #     self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
    #     self.insert_test_data()
    #     db_stats.delete_user_stats(self.user['id'])
    #     self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
