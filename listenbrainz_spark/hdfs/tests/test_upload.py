import os
import unittest
from unittest.mock import patch, Mock, call

import listenbrainz_spark
from listenbrainz_spark import config, utils, path, schema
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
from listenbrainz_spark.tests import SparkTestCase

from pyspark.sql import Row
from pyspark.sql.types import StructField, StructType, StringType


class HDFSDataUploaderTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = "/test"

    def tearDown(self):
        if utils.path_exists(self.path_):
            utils.delete_dir(self.path_, recursive=True)

    @patch('listenbrainz_spark.utils.read_json')
    @patch('listenbrainz_spark.utils.save_parquet')
    def test_process_json(self, mock_save, mock_read):
        fakeschema = StructType([StructField('xxxxx', StringType(), nullable=True)])
        ListenbrainzDataUploader().process_json('_', '/fakedestpath', '/fakehdfspath', '__', fakeschema)
        mock_read.assert_called_once_with('/fakehdfspath', schema=fakeschema)
        mock_save.assert_called_once_with(mock_read.return_value, '/fakedestpath')

    @patch('listenbrainz_spark.utils.read_json')
    def test_process_json_listens_overwrite(self, mock_read_json):
        fakeschema = StructType([StructField('column_1', StringType()), StructField('column_2', StringType())])

        # Save old dataframe in HDFS
        old_df = utils.create_dataframe(Row(column_1='row_a', column_2='row_a'), fakeschema)
        old_df.union(utils.create_dataframe(Row(column_1='row_b', column_2='row_b'), fakeschema))
        utils.save_parquet(old_df, os.path.join(self.path_, '2020/1.parquet'))

        # Mock read_json to return new dataframe
        new_df = utils.create_dataframe(Row(column_1='row_c', column_2='row_c'), fakeschema)
        mock_read_json.return_value = new_df

        ListenbrainzDataUploader().process_json_listens(os.path.join(self.path_, '2020/1.json'),
                                                        self.path_, self.path_, append=False, schema=fakeschema)

        received = utils.read_files_from_HDFS(os.path.join(self.path_, '2020/1.parquet')) \
            .rdd \
            .map(list) \
            .collect()

        expected = new_df.rdd.map(list).collect()

        self.assertListEqual(received, expected)

    @patch('listenbrainz_spark.utils.read_json')
    def test_process_json_listens_append(self, mock_read_json):
        fakeschema = StructType([StructField('column_1', StringType()), StructField('column_2', StringType())])

        # Save old dataframe in HDFS
        old_df = utils.create_dataframe(Row(column_1='row_a', column_2='row_a'), fakeschema)
        old_df.union(utils.create_dataframe(Row(column_1='row_b', column_2='row_b'), fakeschema))
        utils.save_parquet(old_df, os.path.join(self.path_, '/2020/1.parquet'))

        # Mock read_json to return new dataframe
        new_df = utils.create_dataframe(Row(column_1='row_c', column_2='row_c'), fakeschema)
        mock_read_json.return_value = new_df

        ListenbrainzDataUploader().process_json_listens('/2020/1.json', self.path_, self.path_, append=True, schema=fakeschema)

        received = utils.read_files_from_HDFS(os.path.join(self.path_, '/2020/1.parquet')) \
            .rdd \
            .map(list) \
            .collect()

        old_df.union(new_df)
        expected = old_df.rdd.map(list).collect()

        self.assertCountEqual(received, expected)

    @patch('listenbrainz_spark.hdfs.upload.tempfile.TemporaryDirectory')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.process_json_listens')
    @patch('listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.get_pxz_output')
    @patch('listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.upload_archive')
    @patch('listenbrainz_spark.hdfs.upload.tarfile')
    def test_upload_listens(self, mock_tarfile, mock_archive, mock_pxz, mock_listens, mock_tmp):
        faketar = Mock(name='fakefile.tar')
        fakedir = Mock(name="faketempdir")
        mock_tmp.return_value.__enter__.return_value = fakedir

        ListenbrainzDataUploader().upload_listens(faketar)

        mock_pxz.assert_called_once_with(faketar)
        mock_tarfile.open.assert_called_once_with(fileobj=mock_pxz.return_value.stdout, mode='r|')
        mock_archive.assert_called_once_with(fakedir, mock_tarfile.open().__enter__(),
                                             path.LISTENBRAINZ_DATA_DIRECTORY, schema.listen_schema,
                                             mock_listens, overwrite=False)

    @patch('listenbrainz_spark.hdfs.upload.tempfile.TemporaryDirectory')
    @patch('listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.upload_archive')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.process_json')
    @patch('listenbrainz_spark.hdfs.upload.tarfile')
    def test_upload_mapping(self, mock_tarfile, mock_json, mock_archive, mock_tmp):
        faketar = Mock(name='fakefile.tar')
        fakedir = Mock(name="faketempdir")
        mock_tmp.return_value.__enter__.return_value = fakedir

        ListenbrainzDataUploader().upload_mapping(faketar)

        mock_tarfile.open.assert_called_once_with(name=faketar, mode='r:bz2')
        mock_archive.assert_called_once_with(fakedir, mock_tarfile.open().__enter__(),
                                             path.MBID_MSID_MAPPING, schema.msid_mbid_mapping_schema,
                                             mock_json, overwrite=True)

    @patch('listenbrainz_spark.hdfs.upload.tempfile.TemporaryDirectory')
    @patch('listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.upload_archive')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.process_json')
    @patch('listenbrainz_spark.hdfs.upload.tarfile')
    def test_upload_artist_relation(self, mock_tarfile, mock_json, mock_archive, mock_tmp):
        faketar = Mock(name='fakefile.tar')
        fakedir = Mock(name="faketempdir")
        mock_tmp.return_value.__enter__.return_value = fakedir

        ListenbrainzDataUploader().upload_artist_relation(faketar)

        mock_tarfile.open.assert_called_once_with(name=faketar, mode='r:bz2')
        mock_archive.assert_called_once_with(fakedir, mock_tarfile.open().__enter__(),
                                             path.SIMILAR_ARTIST_DATAFRAME_PATH, schema.artist_relation_schema,
                                             mock_json, overwrite=True)
