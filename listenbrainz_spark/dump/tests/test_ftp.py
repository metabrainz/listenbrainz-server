import os
import unittest
from unittest.mock import patch, call, mock_open

from listenbrainz_spark import config
from listenbrainz_spark.dump import DumpType
from listenbrainz_spark.dump.ftp import ListenBrainzFtpDumpLoader
from listenbrainz_spark.exceptions import DumpNotFoundException, DumpInvalidException


class TestableListenBrainzFTPDownloader(ListenBrainzFtpDumpLoader):

    def load_listens(self, directory, listens_dump_id=None, dump_type: DumpType = DumpType.FULL):
        return '', '', 1


class FTPDownloaderTestCase(unittest.TestCase):

    @patch('ftplib.FTP')
    def test_get_dump_name_to_download(self, mock_ftp_cons):
        dump = ['listenbrainz-01-00000', 'listenbrainz-02-00000']
        req_dump = ListenBrainzFtpDumpLoader().get_dump_name_to_download(dump, 1, 1)
        self.assertEqual(req_dump, 'listenbrainz-01-00000')

        req_dump = ListenBrainzFtpDumpLoader().get_dump_name_to_download(dump, None, 1)
        self.assertEqual(req_dump, 'listenbrainz-02-00000')

        with self.assertRaises(DumpNotFoundException):
            ListenBrainzFtpDumpLoader().get_dump_name_to_download(dump, 3, 1)

    @patch('ftplib.FTP')
    def test_get_listens_dump_file_name(self, mock_ftp_cons):
        filename = ListenBrainzFtpDumpLoader().get_listens_dump_file_name('listenbrainz-dump-17-20190101-000001-full/')
        self.assertEqual('listenbrainz-spark-dump-17-20190101-000001-full.tar', filename)

        filename = ListenBrainzFtpDumpLoader().get_listens_dump_file_name('listenbrainz-dump-17-20190101-000001-incremental/')
        self.assertEqual('listenbrainz-spark-dump-17-20190101-000001-incremental.tar', filename)

    @patch.object(ListenBrainzFtpDumpLoader, 'download_dump')
    @patch.object(ListenBrainzFtpDumpLoader, 'get_listens_dump_file_name')
    @patch.object(ListenBrainzFtpDumpLoader, 'list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_full_dump(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-spark-dump-123-20190101-000000-full.tar'
        dest_path, filename, dump_id = ListenBrainzFtpDumpLoader().download_listens('fakedir', None, dump_type=DumpType.FULL)
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls(
            [call(config.FTP_LISTENS_DIR + 'fullexport/'), call('listenbrainz-dump-123-20190101-000000/')])
        self.assertEqual('listenbrainz-spark-dump-123-20190101-000000-full.tar', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)
        self.assertEqual(dump_id, 123)

    @patch.object(ListenBrainzFtpDumpLoader, 'download_dump')
    @patch.object(ListenBrainzFtpDumpLoader, 'get_listens_dump_file_name')
    @patch.object(ListenBrainzFtpDumpLoader, 'list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_full_dump_by_id(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-spark-dump-45-20190201-000000-full.tar'
        dest_path, filename, dump_id = ListenBrainzFtpDumpLoader().download_listens('fakedir',
                                                                                     listens_dump_id=45,
                                                                                     dump_type=DumpType.FULL)
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls([
            call(config.FTP_LISTENS_DIR + 'fullexport/'),
            call('listenbrainz-dump-45-20190201-000000')
        ])
        self.assertEqual('listenbrainz-spark-dump-45-20190201-000000-full.tar', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)
        self.assertEqual(dump_id, 45)

    @patch.object(ListenBrainzFtpDumpLoader, 'download_dump')
    @patch.object(ListenBrainzFtpDumpLoader, 'get_listens_dump_file_name')
    @patch.object(ListenBrainzFtpDumpLoader, 'list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_incremental_dump(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-spark-dump-123-20190101-000000-incremental.tar'
        dest_path, filename, dump_id = ListenBrainzFtpDumpLoader().download_listens('fakedir', None, dump_type=DumpType.INCREMENTAL)
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls(
            [call(config.FTP_LISTENS_DIR + 'incremental/'), call('listenbrainz-dump-123-20190101-000000/')])
        self.assertEqual('listenbrainz-spark-dump-123-20190101-000000-incremental.tar', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)
        self.assertEqual(dump_id, 123)

    @patch.object(ListenBrainzFtpDumpLoader, 'download_dump')
    @patch.object(ListenBrainzFtpDumpLoader, 'get_listens_dump_file_name')
    @patch.object(ListenBrainzFtpDumpLoader, 'list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_incremental_dump_by_id(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-spark-dump-45-20190201-000000-incremental.tar'
        dest_path, filename, dump_id = ListenBrainzFtpDumpLoader().download_listens('fakedir', listens_dump_id=45,
                                                                                     dump_type=DumpType.INCREMENTAL)
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls([
            call(config.FTP_LISTENS_DIR + 'incremental/'),
            call('listenbrainz-dump-45-20190201-000000')
        ])
        self.assertEqual('listenbrainz-spark-dump-45-20190201-000000-incremental.tar', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)
        self.assertEqual(dump_id, 45)

    @patch.object(ListenBrainzFtpDumpLoader, 'connect')
    def test_init(self, mock_connect):
        TestableListenBrainzFTPDownloader()
        mock_connect.assert_called_once()

    @patch('ftplib.FTP')
    def test_connect(self, mock_ftp_cons):
        TestableListenBrainzFTPDownloader().connect()
        mock_ftp_cons.assert_called_with(config.FTP_SERVER_URI)
        mock_ftp = mock_ftp_cons.return_value
        self.assertTrue(mock_ftp.login.called)

    @patch('ftplib.FTP')
    def test_list(self, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        dirs = TestableListenBrainzFTPDownloader().list_dir()
        self.assertTrue(mock_ftp.retrlines.called)
        self.assertEqual(dirs, [])

    @patch('ftplib.FTP')
    def test_download_file_binary(self, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        with patch('listenbrainz_spark.dump.ftp.open', mock_open(), create=True) as mock_file:
            TestableListenBrainzFTPDownloader().download_file_binary('fake/src', 'fake/dest')
        mock_file.assert_called_once_with('fake/dest', 'wb')
        mock_ftp.retrbinary.assert_called_once_with('RETR {}'.format('fake/src'), mock_file().write)

    @patch('ftplib.FTP')
    @patch.object(ListenBrainzFtpDumpLoader, 'download_file_binary')
    @patch.object(ListenBrainzFtpDumpLoader, 'list_dir', return_value=['fakefile.txt', 'fakefile.txt.sha256'])
    @patch('listenbrainz_spark.dump.ftp.os.remove')
    @patch.object(ListenBrainzFtpDumpLoader, '_calc_sha256', return_value='test')
    @patch.object(ListenBrainzFtpDumpLoader, '_read_sha_file', return_value='test')
    def test_download_dump(self, mock_sha_read, mock_sha_calc, mock_remove, mock_list_dir, mock_binary, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        filename = 'fakefile.txt'
        sha_filename = filename + '.sha256'
        directory = 'fakedir'
        sha_dest_path = os.path.join(directory, sha_filename)
        calls = [call(sha_filename, sha_dest_path), call(filename, 'fakedir/' + filename)]

        with patch('listenbrainz_spark.dump.ftp.open', mock_open(read_data='test'), create=True) as mock_file:
            dest_path = TestableListenBrainzFTPDownloader().download_dump(filename, directory)

        self.assertEqual(os.path.join(directory, filename), dest_path)
        mock_list_dir.assert_called_once()
        mock_binary.assert_has_calls(calls)
        mock_sha_read.assert_called_once_with(sha_dest_path)
        mock_remove.assert_called_once_with(sha_dest_path)
        mock_sha_calc.assert_called_once()
        mock_ftp.cwd.assert_called_once_with('/')

    @patch('ftplib.FTP')
    @patch.object(ListenBrainzFtpDumpLoader, 'list_dir', return_value=['fakefile.txt'])
    def test_download_dump_sha_not_available(self, mock_list_dir, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        filename = 'fakefile.txt'
        directory = 'fakedir'

        self.assertRaises(DumpInvalidException, TestableListenBrainzFTPDownloader().download_dump, filename, directory)

    @patch('ftplib.FTP')
    @patch.object(ListenBrainzFtpDumpLoader, 'download_file_binary')
    @patch.object(ListenBrainzFtpDumpLoader, 'list_dir', return_value=['fakefile.txt', 'fakefile.txt.sha256'])
    @patch('listenbrainz_spark.dump.ftp.os.remove')
    @patch.object(ListenBrainzFtpDumpLoader, '_calc_sha256', return_value='test')
    @patch.object(ListenBrainzFtpDumpLoader, '_read_sha_file', return_value='test2')
    def test_download_dump_sha_not_matching(self, mock_sha_read, mock_sha_calc, mock_remove,
                                            mock_list_dir, mock_binary, mock_ftp_cons):
        filename = 'fakefile.txt'
        directory = 'fakedir'

        self.assertRaises(DumpInvalidException, TestableListenBrainzFTPDownloader().download_dump, filename, directory)

    @patch('ftplib.FTP')
    def test_read_sha_file_(self, mock_ftp_cons):
        mock_ftp = mock_ftp_cons.return_value
        with patch('listenbrainz_spark.dump.open', mock_open(read_data='  test\n filename  \n'), create=True) as mock_file:
            result = TestableListenBrainzFTPDownloader()._read_sha_file("/sha_file.sha256")
            self.assertEqual('test', result)
