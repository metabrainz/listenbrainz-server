import os
import tempfile
from datetime import datetime

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark import utils

from pyspark.sql import Row


class UtilsTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = "/test"
    temp_path_ = "/temp"

    def tearDown(self):
        if utils.path_exists(self.path_):
            utils.delete_dir(self.path_, recursive=True)

        if utils.path_exists(self.temp_path_):
            utils.delete_dir(self.temp_path_, recursive=True)

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

    def test_upload_to_HDFS(self):
        temp_file = tempfile.mkdtemp()
        local_path = os.path.join(temp_file, 'test_file.txt')
        with open(local_path, 'w') as f:
            f.write('test file')
        self.path_ = '/test/upload.parquet'
        utils.upload_to_HDFS(self.path_, local_path)
        status = utils.path_exists(self.path_)
        self.assertTrue(status)

    def test_rename(self):
        utils.create_dir(self.path_)
        test_exists = utils.path_exists(self.path_)
        self.assertTrue(test_exists)
        utils.rename(self.path_, self.temp_path_)
        test_exists = utils.path_exists(self.path_)
        self.assertFalse(test_exists)
        temp_exists = utils.path_exists(self.temp_path_)
        self.assertTrue(temp_exists)
        utils.delete_dir(self.temp_path_)

    def test_copy(self):
        # Test directories
        utils.create_dir(self.path_)
        utils.create_dir(os.path.join(self.path_, "a"))
        utils.create_dir(os.path.join(self.path_, "b"))

        # DataFrames to create parquets
        df_a = utils.create_dataframe([Row(column1=1, column2=2)], schema=None)
        df_b = utils.create_dataframe([Row(column1=3, column2=4)], schema=None)
        df_c = utils.create_dataframe([Row(column1=5, column2=6)], schema=None)

        # Save DataFrames in respective directories
        utils.save_parquet(df_a, os.path.join(self.path_, "a", "df_a.parquet"))
        utils.save_parquet(df_b, os.path.join(self.path_, "b", "df_b.parquet"))
        utils.save_parquet(df_c, os.path.join(self.path_, "df_c.parquet"))

        utils.copy(self.path_, self.temp_path_, overwrite=True)

        # Read copied DataFrame
        cp_df_a = utils.read_files_from_HDFS(os.path.join(self.temp_path_, "a", "df_a.parquet"))
        cp_df_b = utils.read_files_from_HDFS(os.path.join(self.temp_path_, "b", "df_b.parquet"))
        cp_df_c = utils.read_files_from_HDFS(os.path.join(self.temp_path_, "df_c.parquet"))

        # Check if both DataFrames are same
        self.assertListEqual(df_a.rdd.map(list).collect(), cp_df_a.rdd.map(list).collect())
        self.assertListEqual(df_b.rdd.map(list).collect(), cp_df_b.rdd.map(list).collect())
        self.assertListEqual(df_c.rdd.map(list).collect(), cp_df_c.rdd.map(list).collect())
