import json
import os
from collections import defaultdict
from datetime import datetime
from unittest.mock import MagicMock, patch

import listenbrainz_spark.stats.user.artist as artist_stats
from listenbrainz_spark import utils
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats.user.utils import get_latest_listen_ts
from listenbrainz_spark.tests import SparkTestCase
from pyspark.sql import Row


class ArtistIntegrationTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = LISTENBRAINZ_DATA_DIRECTORY

    def tearDown(self):
        path_found = utils.path_exists(self.path_)
        if path_found:
            utils.delete_dir(self.path_, recursive=True)

    def save_dataframe(self):
        now = datetime.now()

        with open(self.path_to_data_file('user_top_artists.json')) as f:
            data = json.load(f)

        df = None
        for entry in data:
            for idx in range(0, entry['count']):
                # Assign listened_at to each listen
                row = utils.create_dataframe(Row(user_name=entry['user_name'], artist_name=entry['artist_name'],
                                                 artist_msid=entry['artist_msid'], artist_mbids=entry['artist_mbids']),
                                             schema=None)
                df = df.union(row) if df else row

        utils.save_parquet(df, os.path.join(self.path_, '{}/{}.parquet'.format(now.year, now.month)))

    def test_get_artists(self):
        self.save_dataframe()
        df = utils.get_listens(datetime.now(), datetime.now(), self.path_)
        df.createOrReplaceTempView('test_view')

        expected = defaultdict(list)
        with open(self.path_to_data_file('user_top_artists.json')) as f:
            data = json.load(f)

        for entry in data:
            expected[entry['user_name']].append({
                'artist_name': entry['artist_name'],
                'artist_msid': entry['artist_msid'],
                'artist_mbids': entry['artist_mbids'],
                'listen_count': entry['count']
            })

        # Sort in descending order w.r.t to listen_count
        for user_name, user_artists in expected.items():
            user_artists.sort(key=lambda artist: artist['listen_count'], reverse=True)

        received = artist_stats.get_artists('test_view')

        self.assertDictEqual(received, expected)


class ArtistUnitTestCase(SparkTestCase):
    @patch('listenbrainz_spark.stats.user.artist.get_latest_listen_ts', return_value=datetime(2020, 5, 20))
    @patch('listenbrainz_spark.stats.user.artist.get_listens')
    @patch('listenbrainz_spark.stats.user.artist.filter_listens')
    @patch('listenbrainz_spark.stats.user.artist.get_artists', return_value='artist_data')
    @patch('listenbrainz_spark.stats.user.artist.create_messages')
    def test_get_artist_week(self, mock_create_messages, mock_get_artists,
                             mock_filter_listens, mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df
        mock_filtered_df = MagicMock()
        mock_filter_listens.return_value = mock_filtered_df

        artist_stats.get_artists_week()
        from_date = datetime(2020, 5, 11)
        to_date = datetime(2020, 5, 18)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_filter_listens.assert_called_with(mock_df, from_date, to_date)
        mock_filtered_df.createOrReplaceTempView.assert_called_with('user_artists_week')
        mock_get_artists.assert_called_with('user_artists_week')
        mock_create_messages.assert_called_with(artist_data='artist_data', stats_type='user_artists',
                                                stats_range='week', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.artist.get_latest_listen_ts', return_value=datetime(2020, 5, 20))
    @patch('listenbrainz_spark.stats.user.artist.get_listens')
    @patch('listenbrainz_spark.stats.user.artist.get_artists', return_value='artist_data')
    @patch('listenbrainz_spark.stats.user.artist.create_messages')
    def test_get_artist_month(self, mock_create_messages, mock_get_artists, mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        artist_stats.get_artists_month()
        from_date = datetime(2020, 5, 1)
        to_date = datetime(2020, 5, 20)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('user_artists_month')
        mock_get_artists.assert_called_with('user_artists_month')
        mock_create_messages.assert_called_with(artist_data='artist_data', stats_type='user_artists',
                                                stats_range='month', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.artist.get_latest_listen_ts', return_value=datetime(2020, 5, 20))
    @patch('listenbrainz_spark.stats.user.artist.get_listens')
    @patch('listenbrainz_spark.stats.user.artist.get_artists', return_value='artist_data')
    @patch('listenbrainz_spark.stats.user.artist.create_messages')
    def test_get_artist_year(self, mock_create_messages, mock_get_artists, mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        artist_stats.get_artists_year()
        from_date = datetime(2020, 1, 1)
        to_date = datetime(2020, 5, 20)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('user_artists_year')
        mock_get_artists.assert_called_with('user_artists_year')
        mock_create_messages.assert_called_with(artist_data='artist_data', stats_type='user_artists',
                                                stats_range='year', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.artist.get_latest_listen_ts', return_value=datetime(2020, 5, 20))
    @patch('listenbrainz_spark.stats.user.artist.get_listens')
    @patch('listenbrainz_spark.stats.user.artist.get_artists', return_value='artist_data')
    @patch('listenbrainz_spark.stats.user.artist.create_messages')
    def test_get_artist_all_time(self, mock_create_messages, mock_get_artists, mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        artist_stats.get_artists_all_time()
        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = datetime(2020, 5, 20)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('user_artists_all_time')
        mock_get_artists.assert_called_with('user_artists_all_time')
        mock_create_messages.assert_called_with(artist_data='artist_data', stats_type='user_artists',
                                                stats_range='all_time', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())
