import json
from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

import listenbrainz_spark.stats.user.listening_activity as listening_activity_stats
import listenbrainz_spark.stats.common.listening_activity as listening_activity_utils
from listenbrainz_spark.stats import (offset_days, offset_months, get_day_end,
                                      get_month_end, run_query)
from listenbrainz_spark.stats.user.tests import StatsTestCase


class ListeningActivityTestCase(StatsTestCase):

    def test_get_listening_activity(self):
        with open(self.path_to_data_file('user_listening_activity.json')) as f:
            expected = json.load(f)
        messages = list(listening_activity_stats.get_listening_activity('all_time'))

        self.assertEqual(messages[0]["type"], "couchdb_data_start")
        self.assertEqual(messages[0]["database"], "listening_activity_all_time")

        self.assertEqual(messages[1]["type"], expected[0]["type"])
        self.assertEqual(messages[1]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(messages[1]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(messages[1]["to_ts"], expected[0]["to_ts"])
        self.assertCountEqual(messages[1]["data"], expected[0]["data"])
        self.assertCountEqual(messages[1]["database"], "listening_activity_all_time")

        self.assertEqual(messages[2]["type"], "couchdb_data_end")
        self.assertEqual(messages[2]["database"], "listening_activity_all_time")

    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.listening_activity.calculate_listening_activity', return_value='activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_week(self, mock_create_messages, _, mock_get_listens):
        listening_activity_stats.get_listening_activity('week')

        from_date = day = datetime(2021, 7, 26)
        to_date = datetime(2021, 8, 9)
        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%A %d %B %Y'), day, get_day_end(day)])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='activity_table', stats_range='week',
                                                from_date=from_date, to_date=to_date,
                                                message_type='user_listening_activity', database=None)

    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.listening_activity.calculate_listening_activity', return_value='activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_month(self, mock_create_messages, _, mock_get_listens):
        listening_activity_stats.get_listening_activity('month')

        from_date = day = datetime(2021, 6, 1)
        to_date = datetime(2021, 8, 1)
        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%d %B %Y'), day, get_day_end(day)])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='activity_table', stats_range='month',
                                                from_date=from_date, to_date=to_date,
                                                message_type='user_listening_activity', database=None)

    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.listening_activity.calculate_listening_activity', return_value='activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_year(self, mock_create_messages, _, mock_get_listens):
        listening_activity_stats.get_listening_activity('year')

        from_date = month = datetime(2019, 1, 1)
        to_date = datetime(2021, 1, 1)
        time_range = []
        while month < to_date:
            time_range.append([month.strftime('%B %Y'), month, get_month_end(month)])
            month = offset_months(month, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='activity_table', stats_range='year',
                                                from_date=from_date, to_date=to_date,
                                                message_type='user_listening_activity', database=None)

    @patch("listenbrainz_spark.stats.common.listening_activity.get_latest_listen_ts")
    def test__get_time_range_bounds(self, mock_listen_ts):
        quarters = [
            datetime(2020, 7, 1),
            datetime(2020, 10, 1),
            datetime(2021, 1, 1),
            datetime(2021, 4, 1),
            datetime(2021, 7, 1),
            datetime(2021, 10, 1)
        ]
        step = relativedelta(days=+1)
        fmt = "%d %B %Y"
        spark_fmt = "dd MMMM y"

        mock_listen_ts.return_value = datetime(2021, 1, 5, 2, 3, 0)
        self.assertEqual((quarters[0], quarters[2], step, fmt, spark_fmt), listening_activity_utils._get_time_range_bounds("quarter"))
        mock_listen_ts.return_value = datetime(2021, 5, 7, 2, 3, 0)
        self.assertEqual((quarters[1], quarters[3], step, fmt, spark_fmt), listening_activity_utils._get_time_range_bounds("quarter"))
        mock_listen_ts.return_value = datetime(2021, 8, 9, 2, 3, 0)
        self.assertEqual((quarters[2], quarters[4], step, fmt, spark_fmt), listening_activity_utils._get_time_range_bounds("quarter"))
        mock_listen_ts.return_value = datetime(2021, 11, 8, 2, 3, 0)
        self.assertEqual((quarters[3], quarters[5], step, fmt, spark_fmt), listening_activity_utils._get_time_range_bounds("quarter"))

        periods = [
            datetime(2020, 1, 1),
            datetime(2020, 7, 1),
            datetime(2021, 1, 1),
            datetime(2021, 7, 1)
        ]
        step = relativedelta(months=+1)
        fmt = "%B %Y"
        spark_fmt = "MMMM y"

        mock_listen_ts.return_value = datetime(2021, 3, 5, 2, 3, 0)
        self.assertEqual((periods[0], periods[2], step, fmt, spark_fmt), listening_activity_utils._get_time_range_bounds("half_yearly"))
        mock_listen_ts.return_value = datetime(2021, 9, 7, 2, 3, 0)
        self.assertEqual((periods[1], periods[3], step, fmt, spark_fmt), listening_activity_utils._get_time_range_bounds("half_yearly"))

        step = relativedelta(days=+1)
        fmt = "%A %d %B %Y"
        spark_fmt = "EEEE dd MMMM y"

        mock_listen_ts.return_value = datetime(2021, 11, 24, 2, 3, 0)
        self.assertEqual(
            (datetime(2021, 11, 15), datetime(2021, 11, 24), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("this_week")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 22, 3, 0, 0)
        self.assertEqual(
            (datetime(2021, 11, 8), datetime(2021, 11, 22), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("this_week")
        )

        mock_listen_ts.return_value = datetime(2021, 11, 24, 2, 3, 0)
        self.assertEqual(
            (datetime(2021, 11, 8), datetime(2021, 11, 22), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("week")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 22, 3, 0, 0)
        self.assertEqual(
            (datetime(2021, 11, 8), datetime(2021, 11, 22), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("week")
        )

        step = relativedelta(days=+1)
        fmt = "%d %B %Y"
        spark_fmt = "dd MMMM y"

        mock_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual(
            (datetime(2021, 10, 1), datetime(2021, 11, 21), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("this_month")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual(
            (datetime(2021, 9, 1), datetime(2021, 11, 1), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("this_month")
        )

        mock_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual(
            (datetime(2021, 9, 1), datetime(2021, 11, 1), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("month")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual(
            (datetime(2021, 9, 1), datetime(2021, 11, 1), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("month")
        )

        step = relativedelta(months=+1)
        fmt = "%B %Y"
        spark_fmt = "MMMM y"

        mock_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual(
            (datetime(2019, 1, 1), datetime(2021, 1, 1), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("year")
        )
        mock_listen_ts.return_value = datetime(2021, 1, 1, 2, 3, 0)
        self.assertEqual(
            (datetime(2019, 1, 1), datetime(2021, 1, 1), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("year")
        )
        mock_listen_ts.return_value = datetime(2021, 1, 1, 2, 1, 0)
        self.assertEqual(
            (datetime(2019, 1, 1), datetime(2021, 1, 1), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("this_year")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual(
            (datetime(2020, 1, 1), datetime(2021, 11, 1), step, fmt, spark_fmt),
            listening_activity_utils._get_time_range_bounds("this_year")
        )
