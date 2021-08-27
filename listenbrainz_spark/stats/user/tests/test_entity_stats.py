import json

from listenbrainz_spark.stats.user.entity import get_entity_all_time
from listenbrainz_spark.stats.user.tests import StatsTestCase


class EntityTestCase(StatsTestCase):

    def test_get_artists(self):
        with open(self.path_to_data_file('user_top_artists_output.json')) as f:
            expected = json.load(f)

        received = get_entity_all_time('artists')
        self.assertCountEqual(list(received), expected)

    def test_get_recordings(self):
        with open(self.path_to_data_file('user_top_recordings_output.json')) as f:
            expected = json.load(f)

        received = get_entity_all_time('recordings')
        self.assertCountEqual(list(received), expected)

    def test_get_releases(self):
        with open(self.path_to_data_file('user_top_releases_output.json')) as f:
            expected = json.load(f)

        received = get_entity_all_time('releases')
        self.assertCountEqual(list(received), expected)

