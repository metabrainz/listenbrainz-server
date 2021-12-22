import json
from listenbrainz_spark.stats.sitewide import entity
from listenbrainz_spark.stats.user.tests import StatsTestCase


class SitewideArtistTestCase(StatsTestCase):

    def test_get_artist(self):
        with open(self.path_to_data_file('sitewide_top_artists_output.json')) as f:
            expected = json.load(f)
        received = list(entity.get_entity_stats('artists', 'all_time'))
        self.assertCountEqual(expected, received)
