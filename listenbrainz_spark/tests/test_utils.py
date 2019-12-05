import unittest

from listenbrainz_spark import utils
from listenbrainz_spark.tests import SparkTestCase

class UtilsTestCase(SparkTestCase):

    def test_create_dataframe(self):
        df = utils.create_dataframe({'column1': 1, 'column2': 2}, schema=None)
        self.assertEqual(df.count(), 1)
        path = 'hdfs://hadoop-master:9000/test_df.parquet'
        utils.save_parquet(df, path)
        received_df = utils.read_files_from_HDFS(path)
        self.assertEqual(received_df.count(), 1)
