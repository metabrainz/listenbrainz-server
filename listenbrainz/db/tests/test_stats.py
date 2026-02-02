import listenbrainz.db.stats as db_stats
from data.model.user_artist_map import UserArtistMapRecord
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
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
