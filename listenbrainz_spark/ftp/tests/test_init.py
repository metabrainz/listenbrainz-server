import os
import unittest
from unittest.mock import patch, mock_open

import listenbrainz_spark
from listenbrainz_spark import config

class FTPTestCase(unittest.TestCase):

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
	def test_download_dump(self, mock_binary, mock_ftp_cons):
		mock_ftp = mock_ftp_cons.return_value
		filename = 'fakefile.txt'
		directory = 'fakedir'
		dest_path = listenbrainz_spark.ftp.ListenBrainzFTPDownloader().download_dump(filename, directory)
		self.assertEqual(os.path.join(directory, filename), dest_path)
		mock_binary.assert_called_once_with(filename, dest_path)
		mock_ftp.cwd.assert_called_once_with('/')
