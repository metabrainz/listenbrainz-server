from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

import listenbrainz_spark.stats
from listenbrainz_spark import utils, stats
from listenbrainz_spark.tests import SparkNewTestCase

from pyspark.sql import Row


class InitTestCase(SparkNewTestCase):
    def test_replace_days(self):
        self.assertEqual(stats.replace_days(datetime(2019, 5, 12), 13), datetime(2019, 5, 13))

    def test_replace_months(self):
        self.assertEqual(stats.replace_months(datetime(2020, 5, 18), 6), datetime(2020, 6, 18))

    def test_offset_months(self):
        d1 = stats.offset_months(datetime(2019, 5, 12), 3, shift_backwards=False)
        d2 = datetime(2019, 8, 12)
        self.assertEqual(d1, d2)
        d1 = stats.offset_months(datetime(2019, 5, 12), 3)
        d2 = datetime(2019, 2, 12)
        self.assertEqual(d1, d2)

    def test_offset_days(self):
        d1 = stats.offset_days(datetime(2019, 5, 12), 3, shift_backwards=False)
        d2 = datetime(2019, 5, 15)
        self.assertEqual(d1, d2)
        d1 = stats.offset_days(datetime(2019, 5, 12), 3)
        d2 = datetime(2019, 5, 9)
        self.assertEqual(d1, d2)

    def test_run_query(self):
        df = utils.create_dataframe([Row(column1=1, column2=2)], schema=None)
        df.createOrReplaceTempView("table")
        new_df = stats.run_query("SELECT * FROM table")
        self.assertEqual(new_df.count(), df.count())

    def test_get_day_end(self):
        day = datetime(2020, 6, 19)
        self.assertEqual(datetime(2020, 6, 19, 23, 59, 59, 999999), stats.get_day_end(day))

    def test_get_month_end(self):
        month = datetime(2020, 6, 1)
        self.assertEqual(datetime(2020, 6, 30, 23, 59, 59, 999999), stats.get_month_end(month))

    def test_get_year_end(self):
        self.assertEqual(datetime(2020, 12, 31, 23, 59, 59, 999999), stats.get_year_end(datetime(2020, 1, 1)))

    def test_get_last_monday(self):
        date = datetime(2020, 5, 19)
        self.assertEqual(datetime(2020, 5, 18), listenbrainz_spark.stats.get_last_monday(date))

    @patch("listenbrainz_spark.stats.get_latest_listen_ts")
    def test_get_dates_for_stats_range(self, mock_get_latest_listen_ts):
        quarters = [
            datetime(2021, 1, 1),
            datetime(2021, 4, 1),
            datetime(2021, 7, 1),
            datetime(2021, 10, 1),
            datetime(2022, 1, 1)
        ]
        mock_get_latest_listen_ts.return_value = datetime(2021, 4, 5, 2, 3, 0)
        self.assertEqual((quarters[0], quarters[1]), stats.get_dates_for_stats_range("quarter"))
        mock_get_latest_listen_ts.return_value = datetime(2021, 8, 7, 2, 3, 0)
        self.assertEqual((quarters[1], quarters[2]), stats.get_dates_for_stats_range("quarter"))
        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 9, 2, 3, 0)
        self.assertEqual((quarters[2], quarters[3]), stats.get_dates_for_stats_range("quarter"))
        mock_get_latest_listen_ts.return_value = datetime(2022, 1, 8, 2, 3, 0)
        self.assertEqual((quarters[3], quarters[4]), stats.get_dates_for_stats_range("quarter"))

        periods = [
            datetime(2020, 7, 1),
            datetime(2021, 1, 1),
            datetime(2021, 7, 1)
        ]
        mock_get_latest_listen_ts.return_value = datetime(2021, 1, 9, 2, 3, 0)
        self.assertEqual((periods[0], periods[1]), stats.get_dates_for_stats_range("half_yearly"))
        mock_get_latest_listen_ts.return_value = datetime(2021, 8, 8, 2, 3, 0)
        self.assertEqual((periods[1], periods[2]), stats.get_dates_for_stats_range("half_yearly"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 24, 2, 3, 0)
        self.assertEqual((datetime(2021, 11, 22), datetime(2021, 11, 29)), stats.get_dates_for_stats_range("this_week"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 22, 3, 0, 0)
        self.assertEqual((datetime(2021, 11, 15), datetime(2021, 11, 22)), stats.get_dates_for_stats_range("this_week"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 24, 2, 3, 0)
        self.assertEqual((datetime(2021, 11, 15), datetime(2021, 11, 22)), stats.get_dates_for_stats_range("week"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 22, 3, 0, 0)
        self.assertEqual((datetime(2021, 11, 15), datetime(2021, 11, 22)), stats.get_dates_for_stats_range("week"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual((datetime(2021, 11, 1), datetime(2021, 12, 1)), stats.get_dates_for_stats_range("this_month"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual((datetime(2021, 10, 1), datetime(2021, 11, 1)), stats.get_dates_for_stats_range("this_month"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual((datetime(2021, 10, 1), datetime(2021, 11, 1)), stats.get_dates_for_stats_range("month"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual((datetime(2021, 10, 1), datetime(2021, 11, 1)), stats.get_dates_for_stats_range("month"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 21, 2, 3, 0)
        self.assertEqual((datetime(2020, 1, 1), datetime(2021, 1, 1)), stats.get_dates_for_stats_range("year"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 1, 1, 2, 3, 0)
        self.assertEqual((datetime(2020, 1, 1), datetime(2021, 1, 1)), stats.get_dates_for_stats_range("year"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 1, 1, 2, 1, 0)
        self.assertEqual((datetime(2020, 1, 1), datetime(2021, 1, 1)), stats.get_dates_for_stats_range("this_year"))

        mock_get_latest_listen_ts.return_value = datetime(2021, 11, 1, 3, 0, 0)
        self.assertEqual((datetime(2021, 1, 1), datetime(2022, 1, 1)), stats.get_dates_for_stats_range("this_year"))
