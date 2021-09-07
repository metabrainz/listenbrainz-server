import json
from listenbrainz_spark.stats.sitewide import entity
from listenbrainz_spark.stats.user.tests import StatsTestCase


class SitwideArtistTestCase(StatsTestCase):

    def test_get_artist(self):
        with open(self.path_to_data_file('sitewide_top_artists_output.json')) as f:
            expected = json.load(f)
        received = list(entity.get_entity_all_time('artists'))
        self.assertCountEqual(expected, received)
