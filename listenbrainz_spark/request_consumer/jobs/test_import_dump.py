import unittest

from unittest.mock import patch, MagicMock
from listenbrainz_spark.utils import create_app
from listenbrainz_spark.request_consumer.jobs.import_dump import import_newest_full_dump_handler


class DumpImporterJobTestCase(unittest.TestCase):

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_listens')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_listens')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile.mkdtemp')
    def test_import_full_dump_handler(self, mock_mkdtemp, mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_mkdtemp.return_value = 'best_dir_ever'
        mock_download.return_value = (MagicMock(), 'listenbrainz-listens-dump-20190101-000000-spark-full.tar.xz')
        messages = import_newest_full_dump_handler()
        mock_download.assert_called_once()
        self.assertEqual(mock_download.call_args[1]['dump_type'], 'full')
        self.assertEqual(mock_download.call_args[1]['directory'], 'best_dir_ever')
        mock_upload.assert_called_once()
        mock_rmtree.assert_called_once_with('best_dir_ever')

        self.assertEqual(len(messages), 1)
        self.assertEqual('listenbrainz-listens-dump-20190101-000000-spark-full.tar.xz', messages[0]['imported_dump'])

