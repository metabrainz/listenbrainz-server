import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from listenbrainz_spark.stats.user import entity
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats.user.tests import StatsTestCase


class UserEntityTestCase(StatsTestCase):

    @classmethod
    def setUpClass(cls):
        super(UserEntityTestCase, cls).setUpClass()
        entity.entity_handler_map['test'] = MagicMock(return_value="sample_test_data")

    @patch('listenbrainz_spark.stats.user.entity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_week(self, mock_create_messages, mock_get_listens):
        entity.get_entity_week('test')

        from_date = datetime(2021, 8, 2, 12, 22, 43)
        to_date = datetime(2021, 8, 9, 12, 22, 43)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='sample_test_data', entity='test', stats_range='week',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.entity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_month(self, mock_create_messages, mock_get_listens):
        entity.get_entity_month('test')

        from_date = datetime(2021, 8, 1, 12, 22, 43)
        to_date = datetime(2021, 8, 9, 12, 22, 43)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='sample_test_data', entity='test', stats_range='month',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.entity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_year(self, mock_create_messages, mock_get_listens):
        entity.get_entity_year('test')

        from_date = datetime(2021, 1, 1, 12, 22, 43)
        to_date = datetime(2021, 8, 9, 12, 22, 43)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='sample_test_data', entity='test', stats_range='year',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.entity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_all_time(self, mock_create_messages, mock_get_listens):
        entity.get_entity_all_time('test')

        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = datetime(2021, 8, 9, 12, 22, 43)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='sample_test_data', entity='test', stats_range='all_time',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    def test_create_messages_recordings(self):
        """ Test to check if the number of recordings are clipped to top 1000 """
        recordings = []
        for i in range(0, 2000):
            recordings.append({
                'artist_name': 'artist_{}'.format(i),
                'artist_mbids': [str(i)],
                'release_name': 'release_{}'.format(i),
                'release_mbid': str(i),
                'recording_name': 'recording_{}'.format(i),
                'recording_mbid': str(i),
                'listen_count': i
            })

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'user_name': "test",
            'recordings': recordings
        }

        messages = entity.create_messages([mock_result], 'recordings', 'all_time', 0, 10)

        message = next(messages)
        received_list = message['data']
        expected_list = recordings[:1000]
        self.assertCountEqual(received_list, expected_list)

        received_count = message['count']
        expected_count = 2000
        self.assertEqual(received_count, expected_count)

    def test_skip_incorrect_artists_stats(self):
        """ Test to check if entries with incorrect data is skipped for top user artists """
        with open(self.path_to_data_file('user_top_artists_incorrect.json')) as f:
            data = json.load(f)

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'user_name': "test",
            'artists': data
        }

        messages = entity.create_messages([mock_result], 'artists', 'all_time', 0, 10)
        received_list = next(messages)['data']

        # Only the first entry in file is valid, all others must be skipped
        self.assertListEqual(data[:1], received_list)

    def test_skip_incorrect_releases_stats(self):
        """ Test to check if entries with incorrect data is skipped for top user releases """
        with open(self.path_to_data_file('user_top_releases_incorrect.json')) as f:
            data = json.load(f)

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'user_name': "test",
            'releases': data
        }

        messages = entity.create_messages([mock_result], 'releases', 'all_time', 0, 10)
        received_list = next(messages)['data']

        # Only the first entry in file is valid, all others must be skipped
        self.assertListEqual(data[:1], received_list)

    def test_skip_incorrect_recordings_stats(self):
        """ Test to check if entries with incorrect data is skipped for top user recordings """
        with open(self.path_to_data_file('user_top_recordings_incorrect.json')) as f:
            data = json.load(f)

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'user_name': "test",
            'recordings': data
        }

        messages = entity.create_messages([mock_result], 'recordings', 'all_time', 0, 10)
        received_list = next(messages)['data']

        # Only the first entry in file is valid, all others must be skipped
        self.assertListEqual(data[:1], received_list)
