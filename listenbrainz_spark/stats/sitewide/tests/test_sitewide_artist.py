import calendar
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

import listenbrainz_spark
import listenbrainz_spark.stats.sitewide.artist as artist_stats
from listenbrainz_spark import utils
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.tests import SparkTestCase


def noop():
    # No operation function
    pass


class SitwideArtistTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = LISTENBRAINZ_DATA_DIRECTORY

    def tearDown(self):
        path_found = utils.path_exists(self.path_)
        if path_found:
            utils.delete_dir(self.path_, recursive=True)

    def test_get_artist(self):
        listens = self._create_listens_table()
        time_range = self._create_time_range_table()

        data = artist_stats.get_artists('listens', date_format='EEEE', use_mapping=False)
        received = []
        for entry in data:
            received.append(entry.asDict(recursive=True))

        with open(self.path_to_data_file('sitewide_top_artists_output.json')) as f:
            expected = json.load(f)

        self.assertCountEqual(expected, received)

    @patch("listenbrainz_spark.stats.sitewide.artist._create_mapped_dataframe")
    def test_get_artist_with_mapping(self, mock_create_mapped_df):
        """ Check if _create_mapped_dataframe is called when use_mapping parameter is set to true """
        listens = self._create_listens_table()
        time_range = self._create_time_range_table()

        mapped_df = MagicMock()
        mock_create_mapped_df.return_value = mapped_df

        artist_stats.get_artists('listens', date_format='MMMM', use_mapping=True)

        mock_create_mapped_df.assert_called_once()

    def _create_listens_table(self) -> list:
        """ Create a listens table by processing the testdata from JSON file and returns the processed data """
        with open(self.path_to_data_file('sitewide_top_artists.json')) as f:
            data = json.load(f)

        listens = []
        for entry in data:
            listens.append((entry['artist_name'], entry['artist_msid'],
                            entry['artist_mbids'], datetime.fromtimestamp(entry['timestamp'])))

        listens_df = listenbrainz_spark.session.createDataFrame(
            listens, schema=["artist_name", "artist_msid", "artist_mbids", "listened_at"])
        listens_df.createOrReplaceTempView('listens')

        return listens

    def _create_time_range_table(self) -> list:
        """ Create time_range table with days of the week with fake from_ts and to_ts """
        time_range = [(calendar.day_name[day], 0, 1) for day in range(0, 7)]
        time_range_df = listenbrainz_spark.session.createDataFrame(time_range, ["time_range", "from_ts", "to_ts"])
        time_range_df.createOrReplaceTempView('time_range')
        return time_range
