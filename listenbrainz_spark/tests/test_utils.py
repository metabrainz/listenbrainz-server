import os
import tempfile
from datetime import datetime

import listenbrainz_spark.listens.data
from listenbrainz_spark.tests import SparkNewTestCase
from listenbrainz_spark import utils
from listenbrainz_spark.hdfs.utils import create_dir
from listenbrainz_spark.hdfs.utils import delete_dir
from listenbrainz_spark.hdfs.utils import path_exists
from listenbrainz_spark.hdfs.utils import upload_to_HDFS
from listenbrainz_spark.hdfs.utils import rename
from pyspark.sql import Row


class UtilsTestCase(SparkNewTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = "/test"
    temp_path_ = "/temp"

    def tearDown(self):
        if path_exists(self.path_):
            delete_dir(self.path_, recursive=True)

        if path_exists(self.temp_path_):
            delete_dir(self.temp_path_, recursive=True)

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
        create_dir(self.path_)
        status = path_exists(self.path_)
        self.assertTrue(status)

    def test_delete_dir(self):
        create_dir(self.path_)
        delete_dir(self.path_)
        status = path_exists(self.path_)
        self.assertFalse(status)

    def test_path_exists(self):
        create_dir(self.path_)
        status = path_exists(self.path_)
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
        upload_to_HDFS(self.path_, local_path)
        status = path_exists(self.path_)
        self.assertTrue(status)

    def test_rename(self):
        create_dir(self.path_)
        test_exists = path_exists(self.path_)
        self.assertTrue(test_exists)
        rename(self.path_, self.temp_path_)
        test_exists = path_exists(self.path_)
        self.assertFalse(test_exists)
        temp_exists = path_exists(self.temp_path_)
        self.assertTrue(temp_exists)
        delete_dir(self.temp_path_)

    def test_get_latest_listen_ts(self):
        self.upload_test_listens()
        self.assertEqual(listenbrainz_spark.listens.data.get_latest_listen_ts(), datetime(2021, 8, 9, 12, 22, 43))
        self.delete_uploaded_listens()
