import os
import unittest
from unittest.mock import patch, call

import listenbrainz_spark
from listenbrainz_spark import config, utils
from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader
from listenbrainz_spark.exceptions import DumpNotFoundException

class FTPDownloaderTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = utils.create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    @patch('ftplib.FTP')
    def test_get_req_dump(self, mock_ftp_cons):
        dump = ['listenbrainz-01-00000', 'listenbrainz-02-00000']
        req_dump = ListenbrainzDataDownloader().get_req_dump(dump, '01', 1)
        self.assertEqual(req_dump, 'listenbrainz-01-00000')

        req_dump = ListenbrainzDataDownloader().get_req_dump(dump, None, 1)
        self.assertEqual(req_dump, 'listenbrainz-02-00000')

        with self.assertRaises(DumpNotFoundException):
            ListenbrainzDataDownloader().get_req_dump(dump, '03', 1)

    @patch('ftplib.FTP')
    def test_get_file_name(self, mock_ftp_cons):
        dump_name = 'listenbrainz-01-00000'
        filename = ListenbrainzDataDownloader().get_file_name(dump_name)
        self.assertEqual(dump_name + '.tar.bz2', filename)

    @patch('ftplib.FTP')
    def test_get_listens_file_name(self, mock_ftp_cons):
        filename = ListenbrainzDataDownloader().get_listens_file_name()
        self.assertEqual(filename, config.TEMP_LISTENS_DUMP)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_file_name')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_req_dump')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_get_spark_dump_path(self, mock_ftp_cons, mock_list_dir, mock_req_dir,
        mock_get_f_name, mock_download_dump):
        mock_ftp = mock_ftp_cons.return_value
        dest_path = ListenbrainzDataDownloader().get_spark_dump_path('fakedir', None, 'fakeftpdir', 4)
        mock_list_dir.assert_called_once()

        mock_req_dir.assert_called_once_with(mock_list_dir.return_value, None, 4)
        mock_ftp.cwd.assert_has_calls([call('fakeftpdir'), call(mock_req_dir.return_value)])

        mock_get_f_name.assert_called_once_with(mock_req_dir.return_value)
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)

    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_spark_dump_path')
    @patch('ftplib.FTP')
    def test_download_msid_mbid_mapping(self, mock_ftp_cons, mock_spark_dump):
        dest_path = ListenbrainzDataDownloader().download_msid_mbid_mapping('/fakedir', 1)
        mock_spark_dump.assert_called_once_with('/fakedir', 1, config.FTP_MSID_MBID_DIR, 3)
        self.assertEqual(dest_path, mock_spark_dump.return_value)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens(self, mock_ftp_cons, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_ftp = mock_ftp_cons.return_value
        dest_path = ListenbrainzDataDownloader().download_listens('fakedir', None)
        mock_list_dir.assert_called_once()
        mock_ftp.cwd.assert_has_calls([call(config.FTP_LISTENS_DIR), call(config.TEMP_LISTENS_DIR)])

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)

    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_spark_dump_path')
    @patch('ftplib.FTP')
    def test_download_artist_relation(self, mock_ftp_cons, mock_spark_dump):
        dest_path = ListenbrainzDataDownloader().download_artist_relation('/fakedir', 1)
        mock_spark_dump.assert_called_once_with('/fakedir', 1, config.FTP_ARTIST_RELATION_DIR, 5)
        self.assertEqual(dest_path, mock_spark_dump.return_value)
