from datetime import datetime
from unittest.mock import MagicMock, patch

import listenbrainz_spark.stats.user.entity as entity_stats
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.tests import SparkTestCase


class EntityTestCase(SparkTestCase):
    def get_test(self, table):
        return '{}_data'.format(table)

    def setUp(self):
        entity_stats.entity_handler_map['test'] = self.get_test

    @patch('listenbrainz_spark.stats.user.entity.get_latest_listen_ts', return_value=datetime(2020, 5, 20))
    @patch('listenbrainz_spark.stats.user.entity.get_listens')
    @patch('listenbrainz_spark.stats.user.entity.filter_listens')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_week(self, mock_create_messages, mock_filter_listens,
                             mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df
        mock_filtered_df = MagicMock()
        mock_filter_listens.return_value = mock_filtered_df

        entity_stats.get_entity_week('test')
        from_date = datetime(2020, 5, 11)
        to_date = datetime(2020, 5, 18)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_filter_listens.assert_called_with(mock_df, from_date, to_date)
        mock_filtered_df.createOrReplaceTempView.assert_called_with('user_test_week')
        mock_create_messages.assert_called_with(data='user_test_week_data', entity='test', stats_range='week',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.entity.get_latest_listen_ts', return_value=datetime(2020, 5, 20))
    @patch('listenbrainz_spark.stats.user.entity.get_listens')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_month(self, mock_create_messages, mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        entity_stats.get_entity_month('test')
        from_date = datetime(2020, 5, 1)
        to_date = datetime(2020, 5, 20)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('user_test_month')
        mock_create_messages.assert_called_with(data='user_test_month_data', entity='test', stats_range='month',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.entity.get_latest_listen_ts', return_value=datetime(2020, 5, 20))
    @patch('listenbrainz_spark.stats.user.entity.get_listens')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_year(self, mock_create_messages, mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        entity_stats.get_entity_year('test')
        from_date = datetime(2020, 1, 1)
        to_date = datetime(2020, 5, 20)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('user_test_year')
        mock_create_messages.assert_called_with(data='user_test_year_data', entity='test', stats_range='year',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.entity.get_latest_listen_ts', return_value=datetime(2020, 5, 20))
    @patch('listenbrainz_spark.stats.user.entity.get_listens')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_all_time(self, mock_create_messages, mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        entity_stats.get_entity_all_time('test')
        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = datetime(2020, 5, 20)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('user_test_all_time')
        mock_create_messages.assert_called_with(data='user_test_all_time_data', entity='test', stats_range='all_time',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    def test_create_messages_recordings(self):
        """ Test to check if the number of recordings are clipped to top 1000 """
        recordings = []
        for i in range(0, 2000):
            recordings.append({
                'artist_name': 'artist_{}'.format(i),
                'artist_msid': str(i),
                'artist_mbids': [str(i)],
                'release_name': 'release_{}'.format(i),
                'release_msid': str(i),
                'release_mbid': str(i),
                'track_name': 'recording_{}'.format(i),
                'recording_mbid': str(i),
                'recording_msid': str(i),
                'listen_count': i
            })

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'user_name': "test",
            'recordings': recordings
        }

        messages = entity_stats.create_messages([mock_result], 'recordings', 'all_time', 0, 10)

        received_list = next(messages)['data']
        expected_list = recordings[:1000]

        self.assertEqual(len(received_list), 1000)
        self.assertListEqual(expected_list, received_list)
