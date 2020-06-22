import datetime

from listenbrainz_spark import utils, stats
from listenbrainz_spark.tests import SparkTestCase

from pyspark.sql import Row


class InitTestCase(SparkTestCase):
    def test_replace_days(self):
        self.assertEqual(stats.replace_days(datetime.datetime(2019, 5, 12), 13), datetime.datetime(2019, 5, 13))

    def test_replace_months(self):
        self.assertEqual(stats.replace_months(datetime.datetime(2020, 5, 18), 6), datetime.datetime(2020, 6, 18))

    def test_adjust_months(self):
        d1 = stats.adjust_months(datetime.datetime(2019, 5, 12), 3, shift_backwards=False)
        d2 = datetime.datetime(2019, 8, 12)
        self.assertEqual(d1, d2)
        d1 = stats.adjust_months(datetime.datetime(2019, 5, 12), 3)
        d2 = datetime.datetime(2019, 2, 12)
        self.assertEqual(d1, d2)

    def test_adjust_days(self):
        d1 = stats.adjust_days(datetime.datetime(2019, 5, 12), 3, shift_backwards=False)
        d2 = datetime.datetime(2019, 5, 15)
        self.assertEqual(d1, d2)
        d1 = stats.adjust_days(datetime.datetime(2019, 5, 12), 3)
        d2 = datetime.datetime(2019, 5, 9)
        self.assertEqual(d1, d2)

    def test_run_query(self):
        df = utils.create_dataframe([Row(column1=1, column2=2)], schema=None)
        utils.register_dataframe(df, "table")
        new_df = stats.run_query("SELECT * FROM table")
        self.assertEqual(new_df.count(), df.count())

    def test_get_day_end(self):
        day = datetime.datetime(2020, 6, 19)
        self.assertEqual(datetime.datetime(2020, 6, 19, 23, 59, 59), stats.get_day_end(day))

    def test_get_month_end(self):
        month = datetime.datetime(2020, 6, 1)
        self.assertEqual(datetime.datetime(2020, 6, 30, 23, 59, 59), stats.get_month_end(month))

    def test_get_year_end(self):
        self.assertEqual(datetime.datetime(2020, 12, 31, 23, 59, 59), stats.get_year_end(2020))
