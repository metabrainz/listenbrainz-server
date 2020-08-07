from datetime import datetime

import listenbrainz_spark.stats.user.utils as user_utils
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark import utils
from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.stats import offset_months, offset_days

from pyspark.sql import Row


class UtilsTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = LISTENBRAINZ_DATA_DIRECTORY

    def tearDown(self):
        path_found = utils.path_exists(self.path_)
        if path_found:
            utils.delete_dir(self.path_, recursive=True)

    def test_get_latest_listen_ts(self):
        date = datetime(2020, 5, 18)
        df = utils.create_dataframe(Row(listened_at=date), schema=None)
        df = df.union(utils.create_dataframe(Row(listened_at=offset_days(date, 7)), schema=None))
        utils.save_parquet(df, '{}/2020/5.parquet'.format(self.path_))

        result = user_utils.get_latest_listen_ts()
        self.assertEqual(date, result)

    def test_filter_listens(self):
        from_date = datetime(2020, 5, 1)
        to_date = datetime(2020, 5, 31)

        df = utils.create_dataframe(Row(listened_at=offset_months(from_date, 1)), None)
        df = df.union(utils.create_dataframe(Row(listened_at=offset_months(to_date, 1, shift_backwards=False)), None))
        df = df.union(utils.create_dataframe(Row(listened_at=offset_days(from_date, 5, shift_backwards=False)), None))
        df = df.union(utils.create_dataframe(Row(listened_at=offset_days(to_date, 5)), None))

        result = user_utils.filter_listens(df, from_date, to_date)
        rows = result.collect()

        self.assertEqual(rows[0]['listened_at'], offset_days(from_date, 5, shift_backwards=False))
        self.assertEqual(rows[1]['listened_at'], offset_days(to_date, 5))

    def test_get_last_monday(self):
        date = datetime(2020, 5, 19)
        self.assertEqual(datetime(2020, 5, 18), user_utils.get_last_monday(date))
