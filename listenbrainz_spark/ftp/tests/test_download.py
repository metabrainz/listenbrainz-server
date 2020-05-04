import os
import unittest
from unittest.mock import patch, call

import listenbrainz_spark
from listenbrainz_spark import config, utils
from listenbrainz_spark.exceptions import DumpNotFoundException
from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader, MAPPING_DUMP_ID_POS, \
        ARTIST_RELATION_DUMP_ID_POS

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
    def test_get_dump_name_to_download(self, mock_ftp_cons):
        dump = ['listenbrainz-01-00000', 'listenbrainz-02-00000']
        req_dump = ListenbrainzDataDownloader().get_dump_name_to_download(dump, 1, 1)
        self.assertEqual(req_dump, 'listenbrainz-01-00000')

        req_dump = ListenbrainzDataDownloader().get_dump_name_to_download(dump, None, 1)
        self.assertEqual(req_dump, 'listenbrainz-02-00000')

        with self.assertRaises(DumpNotFoundException):
            ListenbrainzDataDownloader().get_dump_name_to_download(dump, 3, 1)

    @patch('ftplib.FTP')
    def test_get_dump_archive_name(self, mock_ftp_cons):
        dump_name = 'listenbrainz-01-00000'
        filename = ListenbrainzDataDownloader().get_dump_archive_name(dump_name)
        self.assertEqual(dump_name + '.tar.bz2', filename)

    @patch('ftplib.FTP')
    def test_get_listens_dump_file_name(self, mock_ftp_cons):
        filename = ListenbrainzDataDownloader().get_listens_dump_file_name('listenbrainz-dump-17-20190101-000001-full/')
        self.assertEqual('listenbrainz-listens-dump-17-20190101-000001-spark-full.tar.xz', filename)

        filename = ListenbrainzDataDownloader().get_listens_dump_file_name('listenbrainz-dump-17-20190101-000001-incremental/')
        self.assertEqual('listenbrainz-listens-dump-17-20190101-000001-spark-incremental.tar.xz', filename)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_file_name')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_req_dump')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def download_spark_dump_and_get_path(
            self, mock_ftp_cons, mock_list_dir,
            mock_req_dir, mock_get_f_name, mock_download_dump
        ):
        mock_ftp = mock_ftp_cons.return_value
        dest_path = ListenbrainzDataDownloader().download_spark_dump_and_get_path('fakedir', None, 'fakeftpdir', 4)
        mock_list_dir.assert_called_once()

        mock_req_dir.assert_called_once_with(mock_list_dir.return_value, None, 4)
        mock_ftp.cwd.assert_has_calls([call('fakeftpdir'), call(mock_req_dir.return_value)])

        mock_get_f_name.assert_called_once_with(mock_req_dir.return_value)
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)

    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_spark_dump_and_get_path')
    @patch('ftplib.FTP')
    def test_download_msid_mbid_mapping(self, mock_ftp_cons, mock_spark_dump):
        dest_path = ListenbrainzDataDownloader().download_msid_mbid_mapping('/fakedir', 1)
        mock_spark_dump.assert_called_once_with('/fakedir', 1, config.FTP_MSID_MBID_DIR, MAPPING_DUMP_ID_POS)
        self.assertEqual(dest_path, mock_spark_dump.return_value)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_dump_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_full_dump(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-listens-dump-123-20190101-000000-spark-full.tar.xz'
        dest_path, filename = ListenbrainzDataDownloader().download_listens('fakedir', None, dump_type='full')
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls([call(config.FTP_LISTENS_DIR + 'fullexport/'), call('listenbrainz-dump-123-20190101-000000/')])
        self.assertEqual('listenbrainz-listens-dump-123-20190101-000000-spark-full.tar.xz', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_dump_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_full_dump_by_id(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-listens-dump-45-20190201-000000-spark-full.tar.xz'
        dest_path, filename = ListenbrainzDataDownloader().download_listens('fakedir', listens_dump_id=45, dump_type='full')
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls([
                call(config.FTP_LISTENS_DIR + 'fullexport/'),
                call('listenbrainz-dump-45-20190201-000000')
            ])
        self.assertEqual('listenbrainz-listens-dump-45-20190201-000000-spark-full.tar.xz', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_dump_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_incremental_dump(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-listens-dump-123-20190101-000000-spark-incremental.tar.xz'
        dest_path, filename = ListenbrainzDataDownloader().download_listens('fakedir', None, dump_type='incremental')
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls([call(config.FTP_LISTENS_DIR + 'incremental/'), call('listenbrainz-dump-123-20190101-000000/')])
        self.assertEqual('listenbrainz-listens-dump-123-20190101-000000-spark-incremental.tar.xz', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_dump_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_incremental_dump_by_id(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-listens-dump-45-20190201-000000-spark-incremental.tar.xz'
        dest_path, filename = ListenbrainzDataDownloader().download_listens('fakedir', listens_dump_id=45, 
                dump_type='incremental')
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls([
                call(config.FTP_LISTENS_DIR + 'incremental/'),
                call('listenbrainz-dump-45-20190201-000000')
            ])
        self.assertEqual('listenbrainz-listens-dump-45-20190201-000000-spark-incremental.tar.xz', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)

    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_spark_dump_and_get_path')
    @patch('ftplib.FTP')
    def test_download_artist_relation(self, mock_ftp_cons, mock_spark_dump):
        dest_path = ListenbrainzDataDownloader().download_artist_relation('/fakedir', 1)
        mock_spark_dump.assert_called_once_with(
                '/fakedir', 1, config.FTP_ARTIST_RELATION_DIR, ARTIST_RELATION_DUMP_ID_POS)
        self.assertEqual(dest_path, mock_spark_dump.return_value)
