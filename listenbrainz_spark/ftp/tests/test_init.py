import os
import unittest
from unittest.mock import patch, mock_open, call, MagicMock

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.exceptions import DumpInvalidException
from listenbrainz_spark.tests import SparkNewTestCase


class FTPTestCase(SparkNewTestCase):

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.connect')
    def test_init(self, mock_connect):
        listenbrainz_spark.ftp.ListenBrainzFTPDownloader()
        mock_connect.assert_called_once()

    @patch('ftplib.FTP')
    def test_connect(self, mock_ftp_cons):
        listenbrainz_spark.ftp.ListenBrainzFTPDownloader().connect()
        mock_ftp_cons.assert_called_with(config.FTP_SERVER_URI)
        mock_ftp = mock_ftp_cons.return_value
        self.assertTrue(mock_ftp.login.called)

    @patch('ftplib.FTP')
    def test_list(self, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        dirs = listenbrainz_spark.ftp.ListenBrainzFTPDownloader().list_dir()
        self.assertTrue(mock_ftp.retrlines.called)
        self.assertEqual(dirs, [])

    @patch('ftplib.FTP')
    def test_download_file_binary(self, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        with patch('listenbrainz_spark.ftp.open', mock_open(), create=True) as mock_file:
            listenbrainz_spark.ftp.ListenBrainzFTPDownloader().download_file_binary('fake/src', 'fake/dest')
        mock_file.assert_called_once_with('fake/dest', 'wb')
        mock_ftp.retrbinary.assert_called_once_with('RETR {}'.format('fake/src'), mock_file().write)

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_file_binary')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir', return_value=['fakefile.txt', 'fakefile.txt.sha256'])
    @patch('listenbrainz_spark.ftp.os.remove')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader._calc_sha256', return_value='test')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader._read_sha_file', return_value='test')
    def test_download_dump(self, mock_sha_read, mock_sha_calc, mock_remove, mock_list_dir, mock_binary, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        filename = 'fakefile.txt'
        sha_filename = filename + '.sha256'
        directory = 'fakedir'
        sha_dest_path = os.path.join(directory, sha_filename)
        calls = [call(sha_filename, sha_dest_path), call(filename, 'fakedir/' + filename)]

        with patch('listenbrainz_spark.ftp.open', mock_open(read_data='test'), create=True) as mock_file:
            dest_path = listenbrainz_spark.ftp.ListenBrainzFTPDownloader().download_dump(filename, directory)

        self.assertEqual(os.path.join(directory, filename), dest_path)
        mock_list_dir.assert_called_once()
        mock_binary.assert_has_calls(calls)
        mock_sha_read.assert_called_once_with(sha_dest_path)
        mock_remove.assert_called_once_with(sha_dest_path)
        mock_sha_calc.assert_called_once()
        mock_ftp.cwd.assert_called_once_with('/')

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir', return_value=['fakefile.txt'])
    def test_download_dump_sha_not_available(self, mock_list_dir, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        filename = 'fakefile.txt'
        directory = 'fakedir'

        self.assertRaises(DumpInvalidException,
                          listenbrainz_spark.ftp.ListenBrainzFTPDownloader().download_dump, filename, directory)

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_file_binary')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir', return_value=['fakefile.txt', 'fakefile.txt.sha256'])
    @patch('listenbrainz_spark.ftp.os.remove')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader._calc_sha256', return_value='tset')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader._read_sha_file', return_value='test')
    def test_download_dump_sha_not_matching(self, mock_sha_read, mock_sha_calc, mock_remove,
                                            mock_list_dir, mock_binary, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        filename = 'fakefile.txt'
        directory = 'fakedir'

        with patch('listenbrainz_spark.ftp.open', mock_open(read_data='test'), create=True) as mock_file:
            self.assertRaises(DumpInvalidException,
                              listenbrainz_spark.ftp.ListenBrainzFTPDownloader().download_dump, filename, directory)

    @patch('ftplib.FTP')
    def test_read_sha_file_(self, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        with patch('listenbrainz_spark.ftp.open', mock_open(read_data='  test\n filename  \n'), create=True) as mock_file:
            result = listenbrainz_spark.ftp.ListenBrainzFTPDownloader()._read_sha_file("/sha_file.sha256")
            self.assertEqual('test', result)
