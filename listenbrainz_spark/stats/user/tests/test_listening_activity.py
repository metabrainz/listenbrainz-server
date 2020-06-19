from datetime import datetime
from unittest.mock import MagicMock, patch

import listenbrainz_spark.stats.user.listening_activity as listening_activity_stats
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (adjust_days, adjust_months, get_day_end,
                                      get_month_end, get_year_end, run_query)
from listenbrainz_spark.tests import SparkTestCase


class ListeningActivityTestCase(SparkTestCase):
    @patch('listenbrainz_spark.stats.user.listening_activity.get_latest_listen_ts', return_value=datetime(2020, 6, 19))
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='listening_activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_week(self, mock_create_messages, mock_get_listening_activity,
                                         mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        listening_activity_stats.get_listening_activity_week()
        to_date = datetime(2020, 6, 15)
        from_date = day = datetime(2020, 6, 1)

        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%A %d %B %Y'), day, get_day_end(day)])
            day = adjust_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('listens')
        mock_create_messages.assert_called_with(data='listening_activity_table', stats_range='week',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.listening_activity.get_latest_listen_ts', return_value=datetime(2020, 6, 19))
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='listening_activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_month(self, mock_create_messages, mock_get_listening_activity,
                                          mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        listening_activity_stats.get_listening_activity_month()
        to_date = datetime(2020, 6, 19)
        from_date = day = datetime(2020, 5, 1)

        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%d %B %Y'), day, get_day_end(day)])
            day = adjust_days(day, 1, shift_backwards=False)
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
            month = adjust_months(month, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('listens')
        mock_create_messages.assert_called_with(data='listening_activity_table', stats_range='year',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.user.listening_activity.get_latest_listen_ts', return_value=datetime(2020, 6, 19))
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='listening_activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_all_time(self, mock_create_messages, mock_get_listening_activity,
                                             mock_get_listens, mock_get_latest_listen_ts):
        mock_df = MagicMock()
        mock_get_listens.return_value = mock_df

        listening_activity_stats.get_listening_activity_all_time()
        to_date = datetime(2020, 6, 19)
        from_date = month = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

        time_range = []
        for year in range(from_date.year, to_date.year+1):
            time_range.append([str(year), datetime(year, 1, 1), get_year_end(year)])
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_latest_listen_ts.assert_called_once()
        mock_get_listens.assert_called_with(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
        mock_df.createOrReplaceTempView.assert_called_with('listens')
        mock_create_messages.assert_called_with(data='listening_activity_table', stats_range='all_time',
                                                from_ts=from_date.timestamp(), to_ts=to_date.timestamp())
