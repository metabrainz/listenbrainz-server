import os
from datetime import datetime

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark import utils, hdfs_connection, config

from pyspark.sql import Row

class UtilsTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = '/test'

    def tearDown(self):
        path_found = utils.path_exists(self.path_)
        if path_found:
            utils.delete_dir(self.path_, recursive=True)

    def test_append_dataframe(self):
        hdfs_path = self.path_ + '/test_df.parquet'
        df = utils.create_dataframe([Row(column1=1, column2=2)], schema=None)
        utils.append(df, hdfs_path)
        new_df = utils.read_files_from_HDFS(hdfs_path)
        self.assertEqual(new_df.count(), 1)

        df = utils.create_dataframe([Row(column1=3, column2=4)], schema=None)
        utils.append(df, hdfs_path)
        appended_df = utils.read_files_from_HDFS(hdfs_path)
        self.assertEqual(appended_df.count(), 2)

    def test_create_dataframe(self):
        hdfs_path = self.path_ + '/test_df.parquet'
        df = utils.create_dataframe([Row(column1=1, column2=2)], schema=None)
        self.assertEqual(df.count(), 1)
        utils.save_parquet(df, hdfs_path)

        received_df = utils.read_files_from_HDFS(hdfs_path)
        self.assertEqual(received_df.count(), 1)

    def test_create_dir(self):
        utils.create_dir(self.path_)
        status = utils.path_exists(self.path_)
        self.assertTrue(status)

    def test_delete_dir(self):
        utils.create_dir(self.path_)
        utils.delete_dir(self.path_)
        status = utils.path_exists(self.path_)
        self.assertFalse(status)

    def test_get_listens(self):
        from_date = datetime(2019, 10, 1)
        to_date = datetime(2019, 11, 1)

        df = utils.create_dataframe([Row(column1=1, column2=2)], schema=None)
        dest_path = self.path_ + '/{}/{}.parquet'.format(from_date.year, from_date.month)
        utils.save_parquet(df, dest_path)

        df = utils.create_dataframe([Row(column1=3, column2=4)], schema=None)
        dest_path = self.path_ + '/{}/{}.parquet'.format(to_date.year, to_date.month)
        utils.save_parquet(df, dest_path)

        received_df = utils.get_listens(from_date, to_date, self.path_)
        self.assertEqual(received_df.count(), 2)

    def test_path_exists(self):
        utils.create_dir(self.path_)
        status = utils.path_exists(self.path_)
        self.assertTrue(status)

    def test_save_parquet(self):
        df = utils.create_dataframe([Row(column1=1, column2=2)], schema=None)
        utils.save_parquet(df, self.path_)
        received_df = utils.read_files_from_HDFS(self.path_)
        self.assertEqual(received_df.count(), 1)
