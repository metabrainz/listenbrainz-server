import calendar
import itertools
import json
import operator
from datetime import datetime
from unittest.mock import MagicMock, patch

import listenbrainz_spark
import listenbrainz_spark.stats.user.daily_activity as daily_activity_stats
from listenbrainz_spark import utils
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.tests import SparkTestCase


class DailyActivityTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = LISTENBRAINZ_DATA_DIRECTORY

    def tearDown(self):
        path_found = utils.path_exists(self.path_)
        if path_found:
            utils.delete_dir(self.path_, recursive=True)

    def test_get_daily_activity(self):
        data = self._create_listens_table()
        expected = self._calculate_expected(data)

        received = {}
        result = daily_activity_stats.get_daily_activity()
        for entry in result:
            _dict = entry.asDict(recursive=True)
            received[_dict['user_name']] = _dict['daily_activity']

        weekdays = [calendar.day_name[day] for day in range(0, 7)]
        hours = [hour for hour in range(0, 24)]
        time_range = itertools.product(weekdays, hours)
        time_range_df_expected = listenbrainz_spark.session.createDataFrame(time_range, schema=["day", "hour"]).toLocalIterator()
        time_range_expected = [entry.asDict(recursive=True) for entry in time_range_df_expected]

        time_range_df_received = run_query("SELECT * FROM time_range").toLocalIterator()
        time_range_received = [entry.asDict(recursive=True) for entry in time_range_df_received]

        self.assertListEqual(time_range_expected, time_range_received)
        self.assertDictEqual(expected, received)

    @patch('listenbrainz_spark.stats.user.daily_activity.get_latest_listen_ts', return_value=datetime(2020, 7, 22))
    @patch('listenbrainz_spark.stats.user.daily_activity._get_listens')
    @patch('listenbrainz_spark.stats.user.daily_activity.get_daily_activity', return_value='daily_activity_table')
    @patch('listenbrainz_spark.stats.user.daily_activity.create_messages')
    def test_get_daily_activity_week(self, mock_create_messages, mock_get_daily_activity,
                                     mock_get_listens, mock_get_latest_listen_ts):
        daily_activity_stats.get_daily_activity_week()
        to_date = datetime(2020, 7, 20)
        from_date = day = datetime(2020, 7, 13)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='daily_activity_table', stats_range='week',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.daily_activity.get_latest_listen_ts', return_value=datetime(2020, 7, 22))
    @patch('listenbrainz_spark.stats.user.daily_activity._get_listens')
    @patch('listenbrainz_spark.stats.user.daily_activity.get_daily_activity', return_value='daily_activity_table')
    @patch('listenbrainz_spark.stats.user.daily_activity.create_messages')
    def test_get_daily_activity_month(self, mock_create_messages, mock_get_daily_activity,
                                      mock_get_listens, mock_get_latest_listen_ts):
        daily_activity_stats.get_daily_activity_month()
        to_date = datetime(2020, 7, 22)
        from_date = day = datetime(2020, 7, 1)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='daily_activity_table', stats_range='month',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.daily_activity.get_latest_listen_ts', return_value=datetime(2020, 7, 22))
    @patch('listenbrainz_spark.stats.user.daily_activity._get_listens')
    @patch('listenbrainz_spark.stats.user.daily_activity.get_daily_activity', return_value='daily_activity_table')
    @patch('listenbrainz_spark.stats.user.daily_activity.create_messages')
    def test_get_daily_activity_year(self, mock_create_messages, mock_get_daily_activity,
                                     mock_get_listens, mock_get_latest_listen_ts):
        daily_activity_stats.get_daily_activity_year()
        to_date = datetime(2020, 7, 22)
        from_date = day = datetime(2020, 1, 1)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='daily_activity_table', stats_range='year',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.daily_activity.get_latest_listen_ts', return_value=datetime(2020, 7, 22))
    @patch('listenbrainz_spark.stats.user.daily_activity._get_listens')
    @patch('listenbrainz_spark.stats.user.daily_activity.get_daily_activity', return_value='daily_activity_table')
    @patch('listenbrainz_spark.stats.user.daily_activity.create_messages')
    def test_get_daily_activity_all_time(self, mock_create_messages, mock_get_daily_activity,
                                         mock_get_listens, mock_get_latest_listen_ts):
        daily_activity_stats.get_daily_activity_all_time()
        to_date = datetime(2020, 7, 22)
        from_date = day = datetime(2002, 1, 1)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='daily_activity_table', stats_range='all_time',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    def _create_listens_table(self) -> list:
        """ Create a listens table by processing the testdata from JSON file and returns the processed data """
        with open(self.path_to_data_file('user_daily_activity.json')) as f:
            data = json.load(f)

        processed_data = []
        for entry in data:
            processed_data.append((entry['user_name'], datetime.fromtimestamp(entry['timestamp'])))

        listens_df = listenbrainz_spark.session.createDataFrame(processed_data, schema=["user_name", "listened_at"])
        listens_df.createOrReplaceTempView('listens')

        return processed_data

    def _calculate_expected(self, data: list) -> dict:
        # Truncate datetime object to day and hour
        processed_data = []
        for entry in data:
            dt = entry[1]
            processed_data.append({
                "user_name": entry[0],
                "day": calendar.day_name[dt.weekday()],
                "hour": dt.hour
            })

        # Calculate expected result
        expected = {}
        for entry in processed_data:
            if not entry["user_name"] in expected:
                expected[entry["user_name"]] = []

            found = False
            for time_range in expected[entry["user_name"]]:
                if time_range["day"] == entry["day"] and time_range["hour"] == entry["hour"]:
                    found = True
                    time_range["listen_count"] += 1

            if not found:
                expected[entry["user_name"]].append({
                    "day": entry["day"],
                    "hour": entry["hour"],
                    "listen_count": 1
                })

        # Sort by time ranges by hour
        for user, user_data in expected.items():
            user_data.sort(key=operator.itemgetter('hour', 'day', 'listen_count'))

        return expected
