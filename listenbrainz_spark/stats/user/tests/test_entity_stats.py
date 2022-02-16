import json

from listenbrainz_spark.stats.user.entity import get_entity_stats
from listenbrainz_spark.stats.user.tests import StatsTestCase


class EntityTestCase(StatsTestCase):

    def test_get_artists(self):
        with open(self.path_to_data_file('user_top_artists_output.json')) as f:
            expected = json.load(f)

        received = list(get_entity_stats('artists', 'all_time'))

        self.assertEqual(len(received), len(expected))
        self.assertEqual(received[0]["type"], expected[0]["type"])
        self.assertEqual(received[0]["entity"], expected[0]["entity"])
        self.assertEqual(received[0]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(received[0]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(received[0]["to_ts"], expected[0]["to_ts"])
        self.assertCountEqual(received[0]["data"], expected[0]["data"])

    def test_get_recordings(self):
        with open(self.path_to_data_file('user_top_recordings_output.json')) as f:
            expected = json.load(f)

        received = list(get_entity_stats('recordings', 'all_time'))

        self.assertEqual(len(received), len(expected))
        self.assertEqual(received[0]["type"], expected[0]["type"])
        self.assertEqual(received[0]["entity"], expected[0]["entity"])
        self.assertEqual(received[0]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(received[0]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(received[0]["to_ts"], expected[0]["to_ts"])
        self.assertCountEqual(received[0]["data"], expected[0]["data"])

    def test_get_releases(self):
        with open(self.path_to_data_file('user_top_releases_output.json')) as f:
            expected = json.load(f)

        received = list(get_entity_stats('releases', 'all_time'))

        self.assertEqual(len(received), len(expected))
        self.assertEqual(received[0]["type"], expected[0]["type"])
        self.assertEqual(received[0]["entity"], expected[0]["entity"])
        self.assertEqual(received[0]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(received[0]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(received[0]["to_ts"], expected[0]["to_ts"])
        self.assertCountEqual(received[0]["data"], expected[0]["data"])
