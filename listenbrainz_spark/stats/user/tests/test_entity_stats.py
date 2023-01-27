import json

from listenbrainz_spark.stats.user.entity import get_entity_stats
from listenbrainz_spark.stats.user.tests import StatsTestCase


class EntityTestCase(StatsTestCase):

    def test_get_artists(self):
        self.maxDiff = None
        with open(self.path_to_data_file('user_top_artists_output.json')) as f:
            expected = json.load(f)

        messages = list(get_entity_stats('artists', 'all_time'))

        self.assertEqual(messages[0]["type"], "couchdb_data_start")
        self.assertEqual(messages[0]["database"], "artists_all_time")

        self.assertEqual(messages[1]["type"], expected[0]["type"])
        self.assertEqual(messages[1]["entity"], expected[0]["entity"])
        self.assertEqual(messages[1]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(messages[1]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(messages[1]["to_ts"], expected[0]["to_ts"])
        print(json.dumps(messages[1]["data"], indent=4))
        self.assertCountEqual(messages[1]["data"], expected[0]["data"])
        self.assertCountEqual(messages[1]["database"], "artists_all_time")

        self.assertEqual(messages[2]["type"], "couchdb_data_end")
        self.assertEqual(messages[2]["database"], "artists_all_time")

    def test_get_recordings(self):
        with open(self.path_to_data_file('user_top_recordings_output.json')) as f:
            expected = json.load(f)

        messages = list(get_entity_stats('recordings', 'all_time'))

        self.assertEqual(messages[0]["type"], "couchdb_data_start")
        self.assertEqual(messages[0]["database"], "recordings_all_time")

        received = messages[1]
        self.assertEqual(messages[1]["type"], expected[0]["type"])
        self.assertEqual(messages[1]["entity"], expected[0]["entity"])
        self.assertEqual(messages[1]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(messages[1]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(messages[1]["to_ts"], expected[0]["to_ts"])
        self.assertCountEqual(messages[1]["data"], expected[0]["data"])
        self.assertCountEqual(messages[1]["database"], "recordings_all_time")

        self.assertEqual(messages[2]["type"], "couchdb_data_end")
        self.assertEqual(messages[2]["database"], "recordings_all_time")

    def test_get_releases(self):
        with open(self.path_to_data_file('user_top_releases_output.json')) as f:
            expected = json.load(f)

        messages = list(get_entity_stats('releases', 'all_time'))

        self.assertEqual(messages[0]["type"], "couchdb_data_start")
        self.assertEqual(messages[0]["database"], "releases_all_time")

        self.assertEqual(messages[1]["type"], expected[0]["type"])
        self.assertEqual(messages[1]["entity"], expected[0]["entity"])
        self.assertEqual(messages[1]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(messages[1]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(messages[1]["to_ts"], expected[0]["to_ts"])
        self.assertCountEqual(messages[1]["data"], expected[0]["data"])
        self.assertCountEqual(messages[1]["database"], "releases_all_time")

        self.assertEqual(messages[2]["type"], "couchdb_data_end")
        self.assertEqual(messages[2]["database"], "releases_all_time")
