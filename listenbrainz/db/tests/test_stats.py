import itertools
import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone

import requests

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
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import create_app


class StatsDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(StatsDatabaseTestCase, self).setUp()

    def tearDown(self):
        databases = couchdb.list_databases("")
        for database in databases:
            if database == "_users":
                continue
            databases_url = f"{couchdb.get_base_url()}/{database}"
            requests.delete(databases_url)

    def insert_stats(self, entity, range_, data_file):
        with open(self.path_to_data_file(data_file)) as f:
            original = json.load(f)

        # insert modifies the data in place so make a copy first
        data = deepcopy(original)

        database1, database2 = f"{entity}_{range_}_20220716", f"{entity}_{range_}_20220717"
        from_ts1, to_ts1 = int(datetime(2022, 7, 9).timestamp()), int(datetime(2022, 7, 16).timestamp())
        from_ts2, to_ts2 = int(datetime(2022, 7, 10).timestamp()), int(datetime(2022, 7, 17).timestamp())

        couchdb.create_database(database1)
        db_stats.insert(database1, from_ts1, to_ts1, data)

        couchdb.create_database(database2)
        db_stats.insert(database2, from_ts2, to_ts2, data[:1])
        return original, from_ts1, to_ts1, from_ts2, to_ts2

    def _test_one_stat(self, entity, range_, data_file, model, exclude_count=False):
        original, from_ts1, to_ts1, from_ts2, to_ts2 = self.insert_stats(entity, range_, data_file)

        received = db_stats.get(1, entity, range_, model) \
            .dict(exclude={"count"} if exclude_count else None)

        expected = original[0] | {
            "from_ts": from_ts2,
            "to_ts": to_ts2,
            "last_updated": received["last_updated"],
            "stats_range": range_
        }
        self.assertEqual(received, expected)

        received = db_stats.get(2, entity, range_, model) \
            .dict(exclude={"count"} if exclude_count else None)

        expected = original[1] | {
            "from_ts": from_ts1,
            "to_ts": to_ts1,
            "last_updated": received["last_updated"],
            "stats_range": range_
        }
        self.assertEqual(received, expected)

    def test_user_entity_stats(self):
        entities = ["artists", "releases", "recordings"]
        ranges = ["week", "month", "year"]

        with create_app().app_context():
            for range_ in ranges:
                for entity in entities:
                    with self.subTest(f"{range_} {entity} user stats", entity=entity, range_=range_):
                        self._test_one_stat(
                            entity,
                            range_,
                            f'user_top_{entity}_db_data_for_api_test_{range_}.json',
                            EntityRecord
                        )

                with self.subTest(f"{range_} daily_activity user stats", range_=range_):
                    self._test_one_stat(
                        "daily_activity",
                        range_,
                        f'user_daily_activity_db_data_for_api_test_{range_}.json',
                        DailyActivityRecord,
                        exclude_count=True
                    )

                with self.subTest(f"{range_} listening_activity user stats", range_=range_):
                    self._test_one_stat(
                        "listening_activity",
                        range_,
                        f'user_listening_activity_db_data_for_api_test_{range_}.json',
                        ListeningActivityRecord,
                        exclude_count=True
                    )

                with self.subTest(f"{range_} artist_map user stats", range_=range_):
                    self._test_one_stat(
                        "artist_map",
                        range_,
                        f'user_artist_map_db_data_for_api_test_{range_}.json',
                        UserArtistMapRecord,
                        exclude_count=True
                    )

   # def test_get_sitewide_artists(self):
    #     data_inserted = self.insert_test_data()
    #     result = db_stats.get_sitewide_stats('all_time', 'artists')
    #     self.assertDictEqual(result.dict(exclude={'user_id', 'last_updated'}), data_inserted['sitewide_artists'])
    #
    # def test_delete_user_stats(self):
    #     self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
    #     self.insert_test_data()
    #     db_stats.delete_user_stats(self.user['id'])
    #     self.assertFalse(db_stats.valid_stats_exist(self.user['id'], 7))
