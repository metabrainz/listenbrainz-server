import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import listenbrainz_spark.stats.user.listening_activity as listening_activity_stats
import listenbrainz_spark
from listenbrainz_spark import utils
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.exceptions import HDFSException
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (offset_days, offset_months, get_day_end,
                                      get_month_end, get_year_end, run_query)
from listenbrainz_spark.tests import SparkTestCase
from pyspark.sql import Row


def _mock_get_listens_all_time(from_date: datetime, to_date: datetime):
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../..', 'testdata')
    file_ = os.path.join(path, 'user_listening_activity_all_time.json')
    with open(file_) as f:
        data = json.load(f)

    listens_df = None
    for entry in data:
        if entry['year'] == from_date.year:
            row = utils.create_dataframe(Row(user_name=entry['user_name'], listened_at=from_date), schema=None)
            listens_df = listens_df.union(row) if listens_df else row

    if listens_df is None:
        raise HDFSException('')

    listens_df.createOrReplaceTempView('listens')


class ListeningActivityTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = LISTENBRAINZ_DATA_DIRECTORY

    def tearDown(self):
        path_found = utils.path_exists(self.path_)
        if path_found:
            utils.delete_dir(self.path_, recursive=True)

    def test_get_listening_activity(self):
        with open(self.path_to_data_file('user_listening_activity.json')) as f:
            data = json.load(f)

        # Create a dataframe of four time ranges
        time_range = [
            ['time_range_1', datetime.fromtimestamp(1592587270), datetime.fromtimestamp(1592587279)],
            ['time_range_2', datetime.fromtimestamp(1592587280), datetime.fromtimestamp(1592587289)],
            ['time_range_3', datetime.fromtimestamp(1592587290), datetime.fromtimestamp(1592587299)],
            ['time_range_4', datetime.fromtimestamp(1592587300), datetime.fromtimestamp(1592587309)]
        ]
        time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=listening_activity_stats.time_range_schema)
        time_range_df.createOrReplaceTempView('time_range')

        # Read the listens from the file and parse it into a dataframe
        listens_df = None
        for entry in data:
            row = utils.create_dataframe(Row(user_name=entry['user_name'],
                                             listened_at=datetime.fromtimestamp(entry['timestamp'])), schema=None)
            listens_df = listens_df.union(row) if listens_df else row
        listens_df.createOrReplaceTempView('listens')

        expected = self._calculate_expected(data)

        # Get the result calculated by the function we want to test
        data = listening_activity_stats.get_listening_activity()
        received = {}
        for entry in data:
            _dict = entry.asDict(recursive=True)
            received[_dict['user_name']] = _dict['listening_activity']

        self.assertDictEqual(received, expected)

    @patch('listenbrainz_spark.stats.user.listening_activity.get_latest_listen_ts', return_value=datetime(2020, 9, 10, 12, 10))
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='listening_activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_week(self, mock_create_messages, mock_get_listening_activity,
                                         mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        listening_activity_stats.get_listening_activity_week()
        to_date = datetime(2020, 9, 10, 12, 10)
        from_date = day = datetime(2020, 8, 31)

        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%A %d %B %Y'), day, get_day_end(day)])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('listens')
        mock_create_messages.assert_called_with(data='listening_activity_table', stats_range='week',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.listening_activity.get_latest_listen_ts', return_value=datetime(2020, 6, 19, 12, 10))
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='listening_activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_month(self, mock_create_messages, mock_get_listening_activity,
                                          mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        listening_activity_stats.get_listening_activity_month()
        to_date = datetime(2020, 6, 19, 12, 10)
        from_date = day = datetime(2020, 5, 1)

        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%d %B %Y'), day, get_day_end(day)])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('listens')
        mock_create_messages.assert_called_with(data='listening_activity_table', stats_range='month',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.listening_activity.get_latest_listen_ts', return_value=datetime(2020, 6, 19))
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='listening_activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_year(self, mock_create_messages, mock_get_listening_activity,
                                         mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        listening_activity_stats.get_listening_activity_year()
        to_date = datetime(2020, 6, 19)
        from_date = month = datetime(2019, 1, 1)

        time_range = []
        while month < to_date:
            time_range.append([month.strftime('%B %Y'), month, get_month_end(month)])
            month = offset_months(month, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('listens')
        mock_create_messages.assert_called_with(data='listening_activity_table', stats_range='year',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.listening_activity.get_latest_listen_ts', return_value=datetime(2020, 6, 19))
    @patch('listenbrainz_spark.stats.user.listening_activity._get_listens', side_effect=_mock_get_listens_all_time)
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages',
           side_effect=lambda data, stats_range, from_ts, to_ts: data)
    def test_get_listening_activity_all_time(self, mock_create_messages, mock_get_listens, mock_get_latest_listen_ts):
        with open(self.path_to_data_file('user_listening_activity_all_time.json')) as f:
            data = json.load(f)

        expected = self._calculate_expected_all_time(data)

        # Get the result calculated by the function we want to test
        data = listening_activity_stats.get_listening_activity_all_time()
        received = {}
        for entry in data:
            _dict = entry.asDict(recursive=True)
            received[_dict['user_name']] = _dict['listening_activity']

        self.assertDictEqual(received, expected)

    def _calculate_expected(self, data: dict) -> dict:
        expected = {}
        for entry in data:
            if not entry['user_name'] in expected:
                expected[entry['user_name']] = [
                    {'time_range': 'time_range_1', 'from_ts': 1592587270, 'to_ts': 1592587279, 'listen_count': 0},
                    {'time_range': 'time_range_2', 'from_ts': 1592587280, 'to_ts': 1592587289, 'listen_count': 0},
                    {'time_range': 'time_range_3', 'from_ts': 1592587290, 'to_ts': 1592587299, 'listen_count': 0},
                    {'time_range': 'time_range_4', 'from_ts': 1592587300, 'to_ts': 1592587309, 'listen_count': 0}
                ]
        for entry in data:
            for range_ in expected[entry['user_name']]:
                if range_['from_ts'] <= entry['timestamp'] <= range_['to_ts']:
                    range_['listen_count'] += 1

        return expected

    def _calculate_expected_all_time(self, data: dict) -> dict:
        expected = {}
        for entry in data:
            if not entry['user_name'] in expected:
                expected[entry['user_name']] = [
                    {
                        'time_range': '2017',
                        'from_ts': datetime(2017, 1, 1).timestamp(),
                        'to_ts': datetime(2017, 12, 31, 23, 59, 59).timestamp(),
                        'listen_count': 0
                    },
                    {
                        'time_range': '2018',
                        'from_ts': datetime(2018, 1, 1).timestamp(),
                        'to_ts': datetime(2018, 12, 31, 23, 59, 59).timestamp(),
                        'listen_count': 0
                    },
                    {
                        'time_range': '2019',
                        'from_ts': datetime(2019, 1, 1).timestamp(),
                        'to_ts': datetime(2019, 12, 31, 23, 59, 59).timestamp(),
                        'listen_count': 0
                    },
                    {
                        'time_range': '2020',
                        'from_ts': datetime(2020, 1, 1).timestamp(),
                        'to_ts': datetime(2020, 12, 31, 23, 59, 59).timestamp(),
                        'listen_count': 0
                    }
                ]

        for entry in data:
            for range_ in expected[entry['user_name']]:
                if range_['time_range'] == str(entry['year']):
                    range_['listen_count'] += 1

        # Remove entries with zero listens
        for entry in data:
            expected[entry['user_name']] = [range_ for range_ in expected[entry['user_name']] if range_['listen_count'] > 0]

        return expected
