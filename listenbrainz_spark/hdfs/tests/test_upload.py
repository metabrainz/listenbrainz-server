import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch, Mock
from datetime import datetime

import tarfile

from listenbrainz_spark import utils, path, schema
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
from listenbrainz_spark.path import LISTENBRAINZ_NEW_DATA_DIRECTORY
from listenbrainz_spark.tests import SparkNewTestCase

from pyspark.sql.types import StructField, StructType, StringType

from listenbrainz_spark.utils import get_listen_files_list, get_listens_from_dump


class HDFSDataUploaderTestCase(SparkNewTestCase):

    TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'testdata')

    def tearDown(self):
        self.delete_uploaded_listens()

    @patch('listenbrainz_spark.utils.read_json')
    @patch('listenbrainz_spark.utils.save_parquet')
    def test_process_json(self, mock_save, mock_read):
        fakeschema = StructType([StructField('xxxxx', StringType(), nullable=True)])
        ListenbrainzDataUploader().process_json('_', '/fakedestpath', '/fakehdfspath', '__', fakeschema)
        mock_read.assert_called_once_with('/fakehdfspath', schema=fakeschema)
        mock_save.assert_called_once_with(mock_read.return_value, '/fakedestpath')

    def test_upload_listens(self):
        full_dump_tar = self.create_temp_listens_tar('full-dump')
        self.uploader.upload_new_listens_full_dump(full_dump_tar.name)
        self.assertListEqual(
            get_listen_files_list(),
            ["6.parquet", "5.parquet", "4.parquet", "3.parquet",
             "2.parquet", "1.parquet", "0.parquet"]
        )

        incremental_dump_tar = self.create_temp_listens_tar('incremental-dump-1')
        self.uploader.upload_new_listens_incremental_dump(incremental_dump_tar.name)
        self.assertListEqual(
            get_listen_files_list(),
            ["incremental.parquet", "6.parquet", "5.parquet", "4.parquet",
             "3.parquet", "2.parquet", "1.parquet", "0.parquet"]
        )

    def test_upload_incremental_listens(self):
        """ Test incremental listen imports work correctly when there are no
        existing incremental dumps and when there are existing incremental dumps"""
        incremental_dump_tar_1 = self.create_temp_listens_tar('incremental-dump-1')
        self.uploader.upload_new_listens_incremental_dump(incremental_dump_tar_1.name)
        listens = self.get_all_test_listens()
        self.assertEqual(listens.count(), 9)

        incremental_dump_tar_2 = self.create_temp_listens_tar('incremental-dump-2')
        self.uploader.upload_new_listens_incremental_dump(incremental_dump_tar_2.name)
        listens = self.get_all_test_listens()
        # incremental-dump-1 has 9 listens and incremental-dump-2 has 8
        self.assertEqual(listens.count(), 17)

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
