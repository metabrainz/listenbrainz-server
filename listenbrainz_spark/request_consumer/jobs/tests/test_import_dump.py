from datetime import datetime
from unittest.mock import MagicMock, call, patch

from listenbrainz_spark.request_consumer.jobs import import_dump
from listenbrainz_spark.exceptions import (DumpInvalidException,
                                           DumpNotFoundException)
from listenbrainz_spark.path import IMPORT_METADATA
from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.utils import (delete_dir, path_exists,
                                      read_files_from_HDFS)


def mock_import_dump_to_hdfs(dump_type: str, overwrite: bool, dump_id: int):
    """ Mock function returning dump name all dump ids less than 210, else raising DumpNotFoundException """
    if (dump_id < 210):
        return f"listenbrainz-listens-dump-{dump_id}-spark-incremental.tar.xz"
    else:
        raise DumpNotFoundException


def mock_import_dump_to_hdfs_error(dump_type: str, overwrite: bool, dump_id: int):
    """ Mock function returning dump name all dump ids less than 210, else raise DumpInvalidException"""
    if (dump_id < 210) or (dump_id > 210 and dump_id < 213):
        return f"listenbrainz-listens-dump-{dump_id}-spark-incremental.tar.xz"
    elif dump_id == 210:
        raise DumpInvalidException
    else:
        raise DumpNotFoundException


def mock_search_dump(dump_id: int, dump_type: str, imported_at: datetime):
    """ Mock function which returns True for all IDs not divisible by 3, else returns False """
    return dump_id % 3 != 0


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
    def test_import_full_dump_handler(self, mock_datetime, mock_temp, mock_rmtree,
                                      mock_upload, mock_download, mock_ftp_constructor):
        mock_src = MagicMock()
        mock_temp.mkdtemp.return_value = 'best_dir_ever'
        mock_download.return_value = (mock_src, 'listenbrainz-listens-dump-202-20200915-180002-spark-full.tar.xz', 202)
        mock_datetime.utcnow.return_value = datetime(2020, 8, 18)

        messages = import_dump.import_newest_full_dump_handler()
        mock_download.assert_called_once_with(directory='best_dir_ever', dump_type='full',  listens_dump_id=None)
        mock_upload.assert_called_once_with(mock_src, overwrite=True)
        mock_rmtree.assert_called_once_with('best_dir_ever')

        # Check if appropriate entry has been made in the table
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
        expected_count = import_meta_df \
            .filter(import_meta_df.imported_at == datetime(2020, 8, 18)) \
            .filter("dump_id == 202 AND dump_type == 'full'") \
            .count()

        self.assertEqual(expected_count, 1)
        self.assertEqual(len(messages), 1)
        self.assertListEqual(['listenbrainz-listens-dump-202-20200915-180002-spark-full.tar.xz'], messages[0]['imported_dump'])

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_listens')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_listens')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.datetime')
    def test_import_full_dump_by_id_handler(self, mock_datetime, mock_temp, mock_rmtree,
                                            mock_upload, mock_download, mock_ftp_constructor):
        mock_src = MagicMock()
        mock_temp.mkdtemp.return_value = 'best_dir_ever'
        mock_download.return_value = (mock_src, 'listenbrainz-listens-dump-202-20200915-180002-spark-full.tar.xz', 202)
        mock_datetime.utcnow.return_value = datetime(2020, 8, 18)

        messages = import_dump.import_full_dump_by_id_handler(202)
        mock_download.assert_called_once_with(directory='best_dir_ever', dump_type='full',  listens_dump_id=202)
        mock_upload.assert_called_once_with(mock_src, overwrite=True)
        mock_rmtree.assert_called_once_with('best_dir_ever')

        # Check if appropriate entry has been made in the table
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
        expected_count = import_meta_df \
            .filter(import_meta_df.imported_at == datetime(2020, 8, 18)) \
            .filter("dump_id == 202 AND dump_type == 'full'") \
            .count()

        self.assertEqual(expected_count, 1)
        self.assertEqual(len(messages), 1)
        self.assertListEqual(['listenbrainz-listens-dump-202-20200915-180002-spark-full.tar.xz'], messages[0]['imported_dump'])

    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.import_dump_to_hdfs', side_effect=mock_import_dump_to_hdfs)
    @patch('listenbrainz_spark.request_consumer.jobs.utils.search_dump', side_effect=mock_search_dump)
    @patch('listenbrainz_spark.request_consumer.jobs.utils.get_latest_full_dump')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.request_consumer')
    def test_import_newest_incremental_dump_handler(self, mock_rc, mock_latest_full_dump, mock_search, mock_import_dump):
        """ Test to make sure required incremental dumps are imported. """
        mock_latest_full_dump.return_value = {
            "dump_id": 202,
            "imported_at": datetime(2020, 9, 29),
            "dump_type": "incremental"
        }
        mock_import_calls = []
        expected_import_list = []
        for dump_id in range(204, 210, 3):
            mock_import_calls.append(call('incremental', False, dump_id))
            expected_import_list.append(f"listenbrainz-listens-dump-{dump_id}-spark-incremental.tar.xz")

        messages = import_dump.import_newest_incremental_dump_handler()

        mock_import_dump.assert_has_calls(mock_import_calls)
        self.assertListEqual(expected_import_list, messages[0]['imported_dump'])

    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.import_dump_to_hdfs', side_effect=mock_import_dump_to_hdfs_error)
    @patch('listenbrainz_spark.request_consumer.jobs.utils.search_dump', side_effect=mock_search_dump)
    @patch('listenbrainz_spark.request_consumer.jobs.utils.get_latest_full_dump')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.request_consumer')
    def test_import_newest_incremental_dump_handler_error(self, mock_rc, mock_latest_full_dump, mock_search, mock_import_dump):
        """ Test to make sure import is aborted if there is a fatal error. """
        mock_latest_full_dump.return_value = {
            "dump_id": 202,
            "imported_at": datetime(2020, 9, 29),
            "dump_type": "incremental"
        }
        mock_import_calls = []
        expected_import_list = []
        for dump_id in range(204, 210, 3):
            mock_import_calls.append(call('incremental', False, dump_id))
            expected_import_list.append(f"listenbrainz-listens-dump-{dump_id}-spark-incremental.tar.xz")

        messages = import_dump.import_newest_incremental_dump_handler()

        mock_import_dump.assert_has_calls(mock_import_calls)
        # Only three calls should be made
        self.assertEqual(mock_import_dump.call_count, 3)
        self.assertListEqual(expected_import_list, messages[0]['imported_dump'])

    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.import_dump_to_hdfs')
    @patch('listenbrainz_spark.request_consumer.jobs.utils.get_latest_full_dump', return_value=None)
    def test_import_newest_incremental_dump_handler_no_full_dump(self, mock_latest_full_dump, mock_import_dump):
        """ Test to make sure only latest incremental dump is imported if no full dump is found """
        mock_import_dump.return_value = 'listenbrainz-listens-dump-202-20200915-180002-spark-incremental.tar.xz'

        messages = import_dump.import_newest_incremental_dump_handler()

        mock_import_dump.assert_called_once_with('incremental', overwrite=False)
        self.assertEqual(len(messages), 1)
        self.assertListEqual(['listenbrainz-listens-dump-202-20200915-180002-spark-incremental.tar.xz'],
                             messages[0]['imported_dump'])

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_listens')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_listens')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.datetime')
    def test_import_incremental_dump_by_id_handler(self, mock_datetime, mock_temp,
                                                   mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_src = MagicMock()
        mock_temp.mkdtemp.return_value = 'best_dir_ever'
        mock_download.return_value = (mock_src, 'listenbrainz-listens-dump-202-20200915-180002-spark-incremental.tar.xz', 202)
        mock_datetime.utcnow.return_value = datetime(2020, 8, 18)

        messages = import_dump.import_incremental_dump_by_id_handler(202)
        mock_download.assert_called_once_with(directory='best_dir_ever', dump_type='incremental',  listens_dump_id=202)
        mock_upload.assert_called_once_with(mock_src, overwrite=False)
        mock_rmtree.assert_called_once_with('best_dir_ever')

        # Check if appropriate entry has been made in the table
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
        expected_count = import_meta_df \
            .filter(import_meta_df.imported_at == datetime(2020, 8, 18)) \
            .filter("dump_id == 202 AND dump_type == 'incremental'") \
            .count()

        self.assertEqual(expected_count, 1)
        self.assertEqual(len(messages), 1)
        self.assertListEqual(['listenbrainz-listens-dump-202-20200915-180002-spark-incremental.tar.xz'],
                             messages[0]['imported_dump'])

    @patch('ftplib.FTP')
    @patch('listenbrainz_spark.ftp.download.ListenbrainzDataDownloader.download_msid_mbid_mapping')
    @patch('listenbrainz_spark.hdfs.upload.ListenbrainzDataUploader.upload_mapping')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.shutil.rmtree')
    @patch('listenbrainz_spark.request_consumer.jobs.import_dump.tempfile')
    def test_import_mapping_to_hdfs(self, mock_temp, mock_rmtree, mock_upload, mock_download, mock_ftp_constructor):
        mock_temp.mkdtemp.return_value = 'fake_dir'
        mock_download.return_value = ('download_dir', 'msid-mbid-mapping-with-matchable-20200603-202731.tar.bz2')
        message = import_dump.import_mapping_to_hdfs()

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
        message = import_dump.import_artist_relation_to_hdfs()

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
