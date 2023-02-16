import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from listenbrainz_spark.stats.user import entity
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats.user.tests import StatsTestCase


class UserEntityTestCase(StatsTestCase):

    @classmethod
    def setUpClass(cls):
        super(UserEntityTestCase, cls).setUpClass()
        entity.entity_handler_map['test'] = MagicMock(return_value="sample_test_data")

    @patch('listenbrainz_spark.stats.user.entity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_week(self, mock_create_messages, mock_get_listens):
        entity.get_entity_stats('test', 'week')

        from_date = datetime(2021, 8, 2)
        to_date = datetime(2021, 8, 9)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='sample_test_data', entity='test', stats_range='week',
                                                from_date=from_date, to_date=to_date, message_type="user_entity",
                                                database=None)

    @patch('listenbrainz_spark.stats.user.entity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_month(self, mock_create_messages, mock_get_listens):
        entity.get_entity_stats('test', 'month')

        from_date = datetime(2021, 7, 1)
        to_date = datetime(2021, 8, 1)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='sample_test_data', entity='test', stats_range='month',
                                                from_date=from_date, to_date=to_date, message_type="user_entity",
                                                database=None)

    @patch('listenbrainz_spark.stats.user.entity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_year(self, mock_create_messages, mock_get_listens):
        entity.get_entity_stats('test', 'year')

        from_date = datetime(2020, 1, 1)
        to_date = datetime(2021, 1, 1)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='sample_test_data', entity='test', stats_range='year',
                                                from_date=from_date, to_date=to_date, message_type="user_entity",
                                                database=None)

    @patch('listenbrainz_spark.stats.user.entity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.entity.create_messages')
    def test_get_entity_all_time(self, mock_create_messages, mock_get_listens):
        entity.get_entity_stats('test', 'all_time')

        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = datetime(2021, 8, 9, 12, 22, 43)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='sample_test_data', entity='test', stats_range='all_time',
                                                from_date=from_date, to_date=to_date, message_type="user_entity",
                                                database=None)

    def test_skip_incorrect_artists_stats(self):
        """ Test to check if entries with incorrect data is skipped for top user artists """
        with open(self.path_to_data_file('user_top_artists_incorrect.json')) as f:
            data = json.load(f)

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'user_id': 1,
            'artists': data,
            'artists_count': 3
        }

        messages = entity.create_messages([mock_result], 'artists', 'all_time',
                                          datetime.now(), datetime.now(), "user_entity")
        next(messages)  # skip couchdb database create message
        received_list = next(messages)["data"][0]["data"]

        # Only the first entry in file is valid, all others must be skipped
        self.assertListEqual(data[:1], received_list)

    def test_skip_incorrect_releases_stats(self):
        """ Test to check if entries with incorrect data is skipped for top user releases """
        with open(self.path_to_data_file('user_top_releases_incorrect.json')) as f:
            data = json.load(f)

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'user_id': 1,
            'releases': data,
            'releases_count': 3
        }

        messages = entity.create_messages([mock_result], 'releases', 'all_time',
                                          datetime.now(), datetime.now(), "user_entity")
        next(messages)  # skip couchdb database create message
        received_list = next(messages)["data"][0]["data"]

        # Only the first entry in file is valid, all others must be skipped
        self.assertListEqual(data[:1], received_list)

    def test_skip_incorrect_recordings_stats(self):
        """ Test to check if entries with incorrect data is skipped for top user recordings """
        with open(self.path_to_data_file('user_top_recordings_incorrect.json')) as f:
            data = json.load(f)

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'user_id': 1,
            'recordings': data,
            'recordings_count': 4
        }

        messages = entity.create_messages([mock_result], 'recordings', 'all_time',
                                          datetime.now(), datetime.now(), "user_entity")
        next(messages)  # skip couchdb database create message
        received_list = next(messages)["data"][0]["data"]

        # Only the first entry in file is valid, all others must be skipped
        self.assertListEqual(data[:1], received_list)
