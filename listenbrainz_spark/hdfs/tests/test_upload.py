import unittest
from unittest.mock import patch, Mock, call

import listenbrainz_spark
from listenbrainz_spark import config, utils, path, schema
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader

from pyspark.sql.types import StructField, StructType, StringType

class HDFSDataUploaderTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = utils.create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    @patch('listenbrainz_spark.utils.read_json')
    @patch('listenbrainz_spark.utils.save_parquet')
    def test_process_json(self, mock_save, mock_read):
        fakeschema = StructType([StructField('xxxxx', StringType(), nullable=True)])
        ListenbrainzDataUploader().process_json('fakename', '/fakedestpath', '/fakehdfspath', fakeschema)
        mock_read.assert_called_once_with('/fakehdfspath', schema=fakeschema)
        mock_save.assert_called_once_with(mock_read.return_value, '/fakedestpath')

    @patch('listenbrainz_spark.utils.read_json')
    @patch('listenbrainz_spark.utils.save_parquet')
    def test_process_json_listens(self, mock_save, mock_read):
        fakeschema = StructType([StructField('xxxxx', StringType(), nullable=True)])
        ListenbrainzDataUploader().process_json_listens('/2020/1.json', '/fakedir', 'fakehdfspath', fakeschema)
        mock_read.assert_called_once_with('fakehdfspath', schema=fakeschema)
        mock_save.assert_called_once_with(mock_read.return_value, '/fakedir/2020/1.parquet')

    @patch('listenbrainz_spark.hdfs.upload.tempfile')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.process_json_listens')
    @patch('listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.get_pxz_output')
    @patch('listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.upload_archive')
    @patch('listenbrainz_spark.hdfs.upload.tarfile')
    def test_upload_listens(self, mock_tarfile, mock_archive, mock_pxz, mock_listens, mock_tmp):
        faketar = Mock(name='fakefile.tar')
        ListenbrainzDataUploader().upload_listens(faketar)
        mock_pxz.assert_called_once_with(faketar)
        mock_tarfile.open.assert_called_once_with(fileobj=mock_pxz.return_value.stdout, mode='r|')
        mock_archive.assert_called_once_with(mock_tmp.mkdtemp(), mock_tarfile.open().__enter__(),
            path.LISTENBRAINZ_DATA_DIRECTORY, schema.listen_schema, mock_listens, force=False)

    @patch('listenbrainz_spark.hdfs.upload.tempfile')
    @patch('listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.upload_archive')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.process_json')
    @patch('listenbrainz_spark.hdfs.upload.tarfile')
    def test_upload_mapping(self, mock_tarfile, mock_json, mock_archive, mock_tmp):
        faketar = Mock(name='fakefile.tar')
        ListenbrainzDataUploader().upload_mapping(faketar)
        mock_tarfile.open.assert_called_once_with(name=faketar, mode='r:bz2')
        mock_archive.assert_called_once_with(mock_tmp.mkdtemp(), mock_tarfile.open().__enter__(),
            path.MBID_MSID_MAPPING, schema.msid_mbid_mapping_schema, mock_json, force=False)

    @patch('listenbrainz_spark.hdfs.upload.tempfile')
    @patch('listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.upload_archive')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.process_json')
    @patch('listenbrainz_spark.hdfs.upload.tarfile')
    def test_upload_artist_relation(self, mock_tarfile, mock_json, mock_archive, mock_tmp):
        faketar = Mock(name='fakefile.tar')
        ListenbrainzDataUploader().upload_artist_relation(faketar)
        mock_tarfile.open.assert_called_once_with(name=faketar, mode='r:bz2')
        mock_archive.assert_called_once_with(mock_tmp.mkdtemp(), mock_tarfile.open().__enter__(),
            path.SIMILAR_ARTIST_DATAFRAME_PATH, schema.artist_relation_schema, mock_json, force=False)
