from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from listenbrainz_spark.stats import (offset_days, offset_months, get_day_end,
                                      get_month_end, run_query)
from listenbrainz_spark.stats.common.listening_activity import get_time_range_bounds
from listenbrainz_spark.stats.incremental.range_selector import ListeningActivityListenRangeSelector
from listenbrainz_spark.stats.incremental.user.listening_activity import ListeningActivityUserStatsQueryEntity
from listenbrainz_spark.tests import SparkNewTestCase


class ListeningActivityListenRangeSelectorTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upload_test_listens()

    @classmethod
    def tearDownClass(cls):
        cls.delete_uploaded_listens()
        super().tearDownClass()

    def test_get_listening_activity_week(self):
        selector = ListeningActivityListenRangeSelector("week")
        ListeningActivityUserStatsQueryEntity(selector)

        from_date = day = datetime(2021, 7, 26)
        to_date = datetime(2021, 8, 9)
        time_range = []
        while day < to_date:
            time_range.append([day.strftime("%A %d %B %Y"), day, get_day_end(day)])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")

        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

    def test_get_listening_activity_month(self):
        selector = ListeningActivityListenRangeSelector("month")
        ListeningActivityUserStatsQueryEntity(selector)

        from_date = day = datetime(2021, 6, 1)
        to_date = datetime(2021, 8, 1)
        time_range = []
        while day < to_date:
            time_range.append([day.strftime("%d %B %Y"), day, get_day_end(day)])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

    def test_get_listening_activity_year(self):
        selector = ListeningActivityListenRangeSelector("year")
        ListeningActivityUserStatsQueryEntity(selector)
        
        from_date = month = datetime(2019, 1, 1)
        to_date = datetime(2021, 1, 1)
        time_range = []
        while month < to_date:
            time_range.append([month.strftime("%B %Y"), month, get_month_end(month)])
            month = offset_months(month, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

    @patch("listenbrainz_spark.stats.common.listening_activity.get_latest_listen_ts")
    def test_get_time_range_bounds(self, mock_listen_ts):
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
        self.assertEqual((quarters[0], quarters[2], step, fmt, spark_fmt), get_time_range_bounds("quarter"))
        mock_listen_ts.return_value = datetime(2021, 5, 7, 2, 3, 0)
        self.assertEqual((quarters[1], quarters[3], step, fmt, spark_fmt), get_time_range_bounds("quarter"))
        mock_listen_ts.return_value = datetime(2021, 8, 9, 2, 3, 0)
        self.assertEqual((quarters[2], quarters[4], step, fmt, spark_fmt), get_time_range_bounds("quarter"))
        mock_listen_ts.return_value = datetime(2021, 11, 8, 2, 3, 0)
        self.assertEqual((quarters[3], quarters[5], step, fmt, spark_fmt), get_time_range_bounds("quarter"))

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
        self.assertEqual((periods[0], periods[2], step, fmt, spark_fmt), get_time_range_bounds("half_yearly"))
        mock_listen_ts.return_value = datetime(2021, 9, 7, 2, 3, 0)
        self.assertEqual((periods[1], periods[3], step, fmt, spark_fmt), get_time_range_bounds("half_yearly"))

        step = relativedelta(days=+1)
        fmt = "%A %d %B %Y"
        spark_fmt = "EEEE dd MMMM y"

        mock_listen_ts.return_value = datetime(2021, 11, 24, 2, 3, 0)
        self.assertEqual(
            (datetime(2021, 11, 15), datetime(2021, 11, 24), step, fmt, spark_fmt),
            get_time_range_bounds("this_week")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 22, 3, 0, 0)
        self.assertEqual(
            (datetime(2021, 11, 8), datetime(2021, 11, 22), step, fmt, spark_fmt),
            get_time_range_bounds("this_week")
        )

        mock_listen_ts.return_value = datetime(2021, 11, 24, 2, 3, 0)
        self.assertEqual(
            (datetime(2021, 11, 8), datetime(2021, 11, 22), step, fmt, spark_fmt),
            get_time_range_bounds("week")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 22, 3, 0, 0)
        self.assertEqual(
            (datetime(2021, 11, 8), datetime(2021, 11, 22), step, fmt, spark_fmt),
            get_time_range_bounds("week")
        )

        step = relativedelta(days=+1)
        fmt = "%d %B %Y"
        spark_fmt = "dd MMMM y"

        mock_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual(
            (datetime(2021, 10, 1), datetime(2021, 11, 21), step, fmt, spark_fmt),
            get_time_range_bounds("this_month")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual(
            (datetime(2021, 9, 1), datetime(2021, 11, 1), step, fmt, spark_fmt),
            get_time_range_bounds("this_month")
        )

        mock_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual(
            (datetime(2021, 9, 1), datetime(2021, 11, 1), step, fmt, spark_fmt),
            get_time_range_bounds("month")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual(
            (datetime(2021, 9, 1), datetime(2021, 11, 1), step, fmt, spark_fmt),
            get_time_range_bounds("month")
        )

        step = relativedelta(months=+1)
        fmt = "%B %Y"
        spark_fmt = "MMMM y"

        mock_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual(
            (datetime(2019, 1, 1), datetime(2021, 1, 1), step, fmt, spark_fmt),
            get_time_range_bounds("year")
        )
        mock_listen_ts.return_value = datetime(2021, 1, 1, 2, 3, 0)
        self.assertEqual(
            (datetime(2019, 1, 1), datetime(2021, 1, 1), step, fmt, spark_fmt),
            get_time_range_bounds("year")
        )
        mock_listen_ts.return_value = datetime(2021, 1, 1, 2, 1, 0)
        self.assertEqual(
            (datetime(2019, 1, 1), datetime(2021, 1, 1), step, fmt, spark_fmt),
            get_time_range_bounds("this_year")
        )
        mock_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual(
            (datetime(2020, 1, 1), datetime(2021, 11, 1), step, fmt, spark_fmt),
            get_time_range_bounds("this_year")
        )
