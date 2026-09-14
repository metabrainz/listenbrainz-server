from unittest import mock

import listenbrainz.db.stats as db_stats
from data.model.user_artist_map import UserArtistMapRecord
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz.db import couchdb
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.tests.utils import insert_test_stats, delete_all_couch_databases
from listenbrainz.webserver import create_app


class StatsDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(StatsDatabaseTestCase, self).setUp()

    def tearDown(self):
        super(StatsDatabaseTestCase, self).tearDown()
        delete_all_couch_databases()

    def _test_one_stat(self, entity, range_, data_file, model, exclude_count=False):
        original, from_ts1, to_ts1, from_ts2, to_ts2 = insert_test_stats(entity, range_, data_file)

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
        entities = ["artists", "releases", "recordings", "release_groups"]
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

    def test_clickhouse_user_entity_stats(self):
        """ ClickHouse stats are read from the ClickHouse stats couchdb instance using the same
        database names as spark. In tests both point at the same server, so the second instance
        is simulated with a database prefix. """
        app = create_app()
        with app.app_context():
            clickhouse_couchdb = couchdb.CouchDBConnection(
                app.config["COUCHDB_USER"], app.config["COUCHDB_ADMIN_KEY"], app.config["COUCHDB_HOST"],
                app.config["COUCHDB_PORT"], f"{app.config['COUCHDB_DATABASE_PREFIX']}clk_"
            )
            with mock.patch.object(db_stats, "_clickhouse_couchdb", clickhouse_couchdb):
                self.assertTrue(db_stats.is_clickhouse_stats_configured())
                original, from_ts1, to_ts1, from_ts2, to_ts2 = insert_test_stats(
                    "clk_artists", "week", "user_top_artists_db_data_for_api_test_week.json"
                )
                # spark database for the same stat does not exist so this must return nothing
                self.assertIsNone(db_stats.get(1, "artists", "week", EntityRecord))

                received = db_stats.get(1, "artists", "week", EntityRecord, clickhouse=True).dict()
                expected = original[0] | {
                    "from_ts": from_ts2,
                    "to_ts": to_ts2,
                    "last_updated": received["last_updated"],
                    "stats_range": "week"
                }
                self.assertEqual(received, expected)

            with mock.patch.object(db_stats, "_clickhouse_couchdb", None):
                self.assertFalse(db_stats.is_clickhouse_stats_configured())
                self.assertIsNone(db_stats.get(1, "artists", "week", EntityRecord, clickhouse=True))
