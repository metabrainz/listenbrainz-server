import unittest
from datetime import datetime

from unittest.mock import patch, MagicMock
from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.utils import read_files_from_HDFS, path_exists, delete_dir
from listenbrainz_spark.path import IMPORT_METADATA
from listenbrainz_spark.request_consumer.jobs.import_dump import (import_newest_full_dump_handler,
                                                                  import_full_dump_by_id_handler,
                                                                  import_mapping_to_hdfs,
                                                                  import_artist_relation_to_hdfs)


class DumpImporterJobTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = IMPORT_METADATA

    def tearDown(self):
        path_found = path_exists(self.path_)
        if path_found:
            delete_dir(self.path_, recursive=True)

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_listens')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_listens')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.datetime')
    def test_import_full_dump_handler(self, mock_datetime, mock_temp, mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_src = MagicMock()
        mock_temp.mkdtemp.return_value = 'best_dir_ever'
        mock_download.return_value = (mock_src, 'listenbrainz-listens-dump-202-20200915-180002-spark-full.tar.xz', 202)
        mock_datetime.utcnow.return_value = datetime(2020, 8, 18)

        messages = import_newest_full_dump_handler()
        mock_download.assert_called_once_with(directory='best_dir_ever', dump_type='full',  listens_dump_id=None)
        mock_upload.assert_called_once_with(mock_src, overwrite=True)
        mock_rmtree.assert_called_once_with('best_dir_ever')

        # Check if appripriate entry has been made in the table
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
        expected_count = import_meta_df \
            .filter(import_meta_df.imported_at == datetime(2020, 8, 18)) \
            .filter("dump_id == 202 AND dump_type == 'full'") \
            .count()

        self.assertEqual(expected_count, 1)
        self.assertEqual(len(messages), 1)
        self.assertEqual(['listenbrainz-listens-dump-202-20200915-180002-spark-full.tar.xz'], messages[0]['imported_dump'])

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_listens')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_listens')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.datetime')
    def test_import_full_dump_by_id_handler(self, mock_datetime, mock_temp, mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_src = MagicMock()
        mock_temp.mkdtemp.return_value = 'best_dir_ever'
        mock_download.return_value = (mock_src, 'listenbrainz-listens-dump-202-20200915-180002-spark-full.tar.xz', 202)
        mock_datetime.utcnow.return_value = datetime(2020, 8, 18)

        messages = import_full_dump_by_id_handler(202)
        mock_download.assert_called_once_with(directory='best_dir_ever', dump_type='full',  listens_dump_id=202)
        mock_upload.assert_called_once_with(mock_src, overwrite=True)
        mock_rmtree.assert_called_once_with('best_dir_ever')

        # Check if appripriate entry has been made in the table
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
        expected_count = import_meta_df \
            .filter(import_meta_df.imported_at == datetime(2020, 8, 18)) \
            .filter("dump_id == 202 AND dump_type == 'full'") \
            .count()

        self.assertEqual(expected_count, 1)
        self.assertEqual(len(messages), 1)
        self.assertEqual(['listenbrainz-listens-dump-202-20200915-180002-spark-full.tar.xz'], messages[0]['imported_dump'])

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_msid_mbid_mapping')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_mapping')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    def test_import_mapping_to_hdfs(self, mock_temp, mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_temp.mkdtemp.return_value = 'fake_dir'
        mock_download.return_value = ('download_dir', 'msid-mbid-mapping-with-matchable-20200603-202731.tar.bz2')
        message = import_mapping_to_hdfs()

        mock_download.assert_called_once()
        self.assertEqual(mock_download.call_args[1]['directory'], 'fake_dir')

        mock_upload.assert_called_once()
        self.assertEqual(mock_upload.call_args[1]['archive'], 'download_dir')

        self.assertEqual(len(message), 1)
        self.assertEqual(message[0]['imported_mapping'], 'msid-mbid-mapping-with-matchable-20200603-202731.tar.bz2')
        self.assertTrue(message[0]['type'], 'import_mapping')
        self.assertTrue('import_time' in message[0])
        self.assertTrue('time_taken_to_import' in message[0])

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_artist_relation')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_artist_relation')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    def test_import_artist_relation_to_hdfs(self, mock_temp, mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_temp.mkdtemp.return_value = 'fake_dir'
        mock_download.return_value = ('download_dir', 'artist-credit-artist-credit-relations-01-20191230-134806.tar.bz2')
        message = import_artist_relation_to_hdfs()

        mock_download.assert_called_once()
        self.assertEqual(mock_download.call_args[1]['directory'], 'fake_dir')

        mock_upload.assert_called_once()
        self.assertEqual(mock_upload.call_args[1]['archive'], 'download_dir')

        self.assertEqual(len(message), 1)
        self.assertEqual(message[0]['imported_artist_relation'],
                         'artist-credit-artist-credit-relations-01-20191230-134806.tar.bz2')
        self.assertTrue(message[0]['type'], 'import_artist_relation')
        self.assertTrue('import_time' in message[0])
        self.assertTrue('time_taken_to_import' in message[0])
