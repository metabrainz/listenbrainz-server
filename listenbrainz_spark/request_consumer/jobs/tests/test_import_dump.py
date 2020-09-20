import unittest

from unittest.mock import patch, MagicMock
from listenbrainz_spark.utils import create_app
from listenbrainz_spark.request_consumer.jobs.import_dump import (import_newest_full_dump_handler,
                                                                  import_full_dump_by_id_handler,
                                                                  import_mapping_to_hdfs,
                                                                  import_artist_relation_to_hdfs)


class DumpImporterJobTestCase(unittest.TestCase):

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_listens')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_listens')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    def test_import_full_dump_handler(self, mock_temp, mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_temp.mkdtemp.return_value = 'best_dir_ever'
        mock_download.return_value = (MagicMock(), 'listenbrainz-listens-dump-20190101-000000-spark-full.tar.xz')
        messages = import_newest_full_dump_handler()
        mock_download.assert_called_once()
        self.assertEqual(mock_download.call_args[1]['dump_type'], 'full')
        self.assertEqual(mock_download.call_args[1]['directory'], 'best_dir_ever')
        mock_upload.assert_called_once()
        mock_rmtree.assert_called_once_with('best_dir_ever')

        self.assertEqual(len(messages), 1)
        self.assertEqual('listenbrainz-listens-dump-20190101-000000-spark-full.tar.xz', messages[0]['imported_dump'])

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_listens')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_listens')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    def test_import_full_dump_by_id_handler(self, mock_temp, mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_temp.mkdtemp.return_value = 'best_dir_ever'
        mock_download.return_value = (MagicMock(), 'listenbrainz-listens-dump-20190101-000000-spark-full.tar.xz')
        messages = import_full_dump_by_id_handler(100)
        mock_download.assert_called_once()
        self.assertEqual(mock_download.call_args[1]['dump_type'], 'full')
        self.assertEqual(mock_download.call_args[1]['directory'], 'best_dir_ever')
        self.assertEqual(mock_download.call_args[1]['listens_dump_id'], 100)
        mock_upload.assert_called_once()
        mock_rmtree.assert_called_once_with('best_dir_ever')

        self.assertEqual(len(messages), 1)
        self.assertEqual('listenbrainz-listens-dump-20190101-000000-spark-full.tar.xz', messages[0]['imported_dump'])

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
