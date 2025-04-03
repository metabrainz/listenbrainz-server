import calendar
import itertools
import json

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.user.daily_activity import get_daily_activity
from listenbrainz_spark.stats.user.entity import get_entity_stats
from listenbrainz_spark.stats.user.listening_activity import get_listening_activity
from listenbrainz_spark.stats.user.tests import StatsTestCase


class UserStatsTestCase(StatsTestCase):

    def _test_helper(self, entity, data_file):
        stats_range = "all_time"
        messages = list(get_entity_stats(entity, stats_range))
        self.assert_user_stats_equal(data_file, messages, f"{entity}_{stats_range}")

    def test_get_artists(self):
        self._test_helper("artists", "user_top_artists_output.json")

    def test_get_recordings(self):
        self._test_helper("recordings", "user_top_recordings_output.json")

    def test_get_releases(self):
        self._test_helper("releases", "user_top_releases_output.json")

    def test_get_release_groups(self):
        self._test_helper("release_groups", "user_top_release_groups_output.json")

    def test_get_listening_activity(self):
        messages = list(get_listening_activity("all_time"))
        self.assert_user_stats_equal(
            "user_listening_activity_all_time.json",
            messages,
            "listening_activity_all_time"
        )

    def test_get_daily_activity(self):
        messages = list(get_daily_activity("all_time"))
        with open(self.path_to_data_file("user_daily_activity_all_time.json")) as f:
            expected = json.load(f)

        database_prefix = "daily_activity_all_time"
        self.assertEqual(messages[0]["type"], "couchdb_data_start")
        self.assertTrue(messages[0]["database"].startswith(database_prefix))

        self.assertEqual(messages[1]["type"], expected[0]["type"])
        self.assertEqual(messages[1]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(messages[1]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(messages[1]["to_ts"], expected[0]["to_ts"])

        self.assertEqual(messages[1]["data"][0]["user_id"], expected[0]["data"][0]["user_id"])
        self.assertCountEqual(messages[1]["data"][0]["data"], expected[0]["data"][0]["data"])
        self.assertEqual(messages[1]["data"][1]["user_id"], expected[0]["data"][1]["user_id"])
        self.assertCountEqual(messages[1]["data"][1]["data"], expected[0]["data"][1]["data"])
        self.assertTrue(messages[1]["database"].startswith(database_prefix))

        self.assertEqual(messages[2]["type"], "couchdb_data_end")
        self.assertTrue(messages[2]["database"].startswith(database_prefix))


        time_range_expected = itertools.product(calendar.day_name, range(0, 24))
        time_range_received = run_query("SELECT * FROM time_range").toLocalIterator()
        self.assertListEqual(list(time_range_expected), list(time_range_received))
