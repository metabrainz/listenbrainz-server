import json

import pytest

from listenbrainz_spark.stats.user.artist import get_artists
from listenbrainz_spark.stats.user.entity import create_messages
from listenbrainz_spark.stats.user.recording import get_recordings
from listenbrainz_spark.stats.user.release import get_releases
from listenbrainz_spark.stats.user.tests import StatsTestCase


class ArtistTestCase(StatsTestCase):

    @pytest.mark.parametrize("entity", ["artists", "recordings", "releases"])
    def test_entity_top_stats(self, entity: str):
        with open(self.path_to_data_file(f'user_top_{entity}_output.json')) as f:
            expected = json.load(f)

        data = get_artists('test_listens')
        received = create_messages(data=data, entity=entity, stats_range='all_time',
                                   from_ts=self.begin_date.timestamp(), to_ts=self.end_date.timestamp())
        self.assertCountEqual(list(received), expected)

    def test_get_recordings(self):
        with open(self.path_to_data_file('user_top_recordings_output.json')) as f:
            expected = json.load(f)

        data = get_recordings('test_listens')
        received = create_messages(data=data, entity='recordings', stats_range='all_time',
                                   from_ts=self.begin_date.timestamp(), to_ts=self.end_date.timestamp())
        self.assertCountEqual(list(received), expected)

    def test_get_releases(self):
        with open(self.path_to_data_file('user_top_releases_output.json')) as f:
            expected = json.load(f)

        data = get_releases('test_listens')
        received = create_messages(data=data, entity='releases', stats_range='all_time',
                                   from_ts=self.begin_date.timestamp(), to_ts=self.end_date.timestamp())
        self.assertCountEqual(list(received), expected)

