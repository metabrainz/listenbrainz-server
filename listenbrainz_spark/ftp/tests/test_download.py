import unittest
from unittest.mock import patch, call

from listenbrainz_spark import config
from listenbrainz_spark.exceptions import DumpNotFoundException
from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader


class FTPDownloaderTestCase(unittest.TestCase):

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
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_latest_mapping')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_available_dumps')
    @patch('ftplib.FTP')
    def test_download_msid_mbid_mapping(self, mock_ftp_cons, mock_available_dump, mock_list_dir,
                                        mock_latest_mapping, mock_download_dump):
        directory = '/fakedir'
        mock_list_dir.return_value = [
            'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2',
            'msid-mbid-mapping-with-text-20180603-202000.tar.bz2',
            'msid-mbid-mapping-with-matchable-20200603-202732.tar.bz2',
            'msid-mbid-mapping-with-matchable-xxxx-20200603-202732.tar.bz2'
            'msid-mbid-mapping-with-matchable-20200603-202732.tar.bz2.md5'
        ]
        mock_available_dump.return_value = [
            'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2',
            'msid-mbid-mapping-with-matchable-20200603-202732.tar.bz2',
        ]
        mock_latest_mapping.return_value = 'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2'
        dest_path, filename = ListenbrainzDataDownloader().download_msid_mbid_mapping(directory)

        mock_ftp_cons.return_value.cwd.assert_called_once_with(config.FTP_MSID_MBID_DIR)
        mock_available_dump.assert_called_once_with(mock_list_dir.return_value, 'msid-mbid-mapping-with-matchable')

        mock_latest_mapping.assert_called_once_with([
            'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2',
            'msid-mbid-mapping-with-matchable-20200603-202732.tar.bz2',
        ])
        mock_download_dump.assert_called_once_with('msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2', directory)
        self.assertEqual(dest_path, mock_download_dump.return_value)
        self.assertEqual(filename, 'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2')

    @patch('ftplib.FTP')
    def test_get_latest_mapping(self, mock_ftp):
        mapping = [
            'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2',
            'msid-mbid-mapping-with-text-20180603-202000.tar.bz2',
            'msid-mbid-mapping-with-matchable-20200603-202732.tar.bz2',
            'msid-mbid-mapping-with-matchable-xxxx-20200603-202732.tar.bz2'
            'msid-mbid-mapping-with-matchable-20200603-202732.tar.bz2.md5'
        ]

        expected_mapping = 'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2'
        latest_mapping = ListenbrainzDataDownloader().get_latest_mapping(mapping)
        self.assertEqual(latest_mapping, expected_mapping)

    @patch('ftplib.FTP')
    def test_get_available_dumps(self, mock_ftp):
        dump = [
            'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2',
            'msid-mbid-mapping-with-text-20180603-202000.tar.bz2',
            'msid-mbid-mapping-with-matchable-20200603-202732.tar.bz2',
            'msid-mbid-mapping-with-matchable-xxxx-20200603-202732.tar.bz2'
            'msid-mbid-mapping-with-matchable-20100603-202732.tar.bz2.md5',
        ]

        mapping = ListenbrainzDataDownloader().get_available_dumps(dump, 'msid-mbid-mapping-with-matchable')

        expected_mapping = [
            'msid-mbid-mapping-with-matchable-20200603-203731.tar.bz2',
            'msid-mbid-mapping-with-matchable-20200603-202732.tar.bz2',
        ]

        self.assertEqual(mapping, expected_mapping)

        dump = [
            'msid-mbid-mapping-with-text-20180603-202000.tar.bz2',
            'msid-mbid-mapping-with-matchable-20100603-202732.tar.bz2.md5',
        ]

        with self.assertRaises(DumpNotFoundException):
            ListenbrainzDataDownloader().get_available_dumps(dump, 'msid-mbid-mapping-with-matchable')

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_dump_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_full_dump(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-listens-dump-123-20190101-000000-spark-full.tar.xz'
        dest_path, filename, dump_id = ListenbrainzDataDownloader().download_listens('fakedir', None, dump_type='full')
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls(
            [call(config.FTP_LISTENS_DIR + 'fullexport/'), call('listenbrainz-dump-123-20190101-000000/')])
        self.assertEqual('listenbrainz-listens-dump-123-20190101-000000-spark-full.tar.xz', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)
        self.assertEqual(dump_id, 123)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_dump_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_full_dump_by_id(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-listens-dump-45-20190201-000000-spark-full.tar.xz'
        dest_path, filename, dump_id = ListenbrainzDataDownloader().download_listens('fakedir',
                                                                                     listens_dump_id=45, dump_type='full')
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls([
            call(config.FTP_LISTENS_DIR + 'fullexport/'),
            call('listenbrainz-dump-45-20190201-000000')
        ])
        self.assertEqual('listenbrainz-listens-dump-45-20190201-000000-spark-full.tar.xz', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)
        self.assertEqual(dump_id, 45)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_dump_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_incremental_dump(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-listens-dump-123-20190101-000000-spark-incremental.tar.xz'
        dest_path, filename, dump_id = ListenbrainzDataDownloader().download_listens('fakedir', None, dump_type='incremental')
        mock_list_dir.assert_called_once()
        mock_ftp.return_value.cwd.assert_has_calls(
            [call(config.FTP_LISTENS_DIR + 'incremental/'), call('listenbrainz-dump-123-20190101-000000/')])
        self.assertEqual('listenbrainz-listens-dump-123-20190101-000000-spark-incremental.tar.xz', filename)

        mock_get_f_name.assert_called_once()
        mock_download_dump.assert_called_once_with(mock_get_f_name.return_value, 'fakedir')
        self.assertEqual(dest_path, mock_download_dump.return_value)
        self.assertEqual(dump_id, 123)

    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_listens_dump_file_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_listens_incremental_dump_by_id(self, mock_ftp, mock_list_dir, mock_get_f_name, mock_download_dump):
        mock_list_dir.return_value = ['listenbrainz-dump-123-20190101-000000/', 'listenbrainz-dump-45-20190201-000000']
        mock_get_f_name.return_value = 'listenbrainz-listens-dump-45-20190201-000000-spark-incremental.tar.xz'
        dest_path, filename, dump_id = ListenbrainzDataDownloader().download_listens('fakedir', listens_dump_id=45,
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
        self.assertEqual(dump_id, 45)

    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.get_dump_archive_name')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.download_dump')
    @patch('listenbrainz_spark.ftp.ListenBrainzFTPDownloader.list_dir')
    @patch('ftplib.FTP')
    def test_download_artist_relation(self, mock_ftp_cons, mock_list_dir, mock_download_dump, mock_dump_archive):
        directory = '/fakedir'
        mock_list_dir.return_value = [
            'artist-credit-artist-credit-relations-01-20191230-134806/',
            'artist-credit-artist-credit-relations-02-20191230-134806/',
        ]
        mock_dump_archive.return_value = 'artist-credit-artist-credit-relations-02-20191230-134806.tar.bz2'
        dest_path, filename = ListenbrainzDataDownloader().download_artist_relation(directory)

        mock_list_dir.assert_called_once()
        mock_ftp_cons.return_value.cwd.assert_has_calls([
            call(config.FTP_ARTIST_RELATION_DIR),
            call('artist-credit-artist-credit-relations-02-20191230-134806/')
        ])

        self.assertEqual('artist-credit-artist-credit-relations-02-20191230-134806.tar.bz2', filename)
        mock_dump_archive.assert_called_once_with('artist-credit-artist-credit-relations-02-20191230-134806/')
        mock_download_dump.assert_called_once_with(mock_dump_archive.return_value, directory)
        self.assertEqual(dest_path, mock_download_dump.return_value)
