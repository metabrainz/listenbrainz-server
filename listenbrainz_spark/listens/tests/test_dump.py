from datetime import datetime, timezone
from unittest import mock
from unittest.mock import MagicMock, call, patch

from listenbrainz_spark.dump import DumpType, ListenbrainzDumpLoader
from listenbrainz_spark.dump.ftp import ListenBrainzFtpDumpLoader
from listenbrainz_spark.exceptions import (DumpInvalidException,
                                           DumpNotFoundException)
from listenbrainz_spark.hdfs.utils import (delete_dir, path_exists)
from listenbrainz_spark.listens.data import get_listens_from_dump
from listenbrainz_spark.listens.dump import import_full_dump_to_hdfs, import_incremental_dump_to_hdfs, \
    import_full_dump_handler, import_incremental_dump_handler
from listenbrainz_spark.path import IMPORT_METADATA
from listenbrainz_spark.tests import SparkNewTestCase
from listenbrainz_spark.utils import (read_files_from_HDFS)


def mock_import_dump_to_hdfs(loader: ListenbrainzDumpLoader, dump_id: int):
    """ Mock function returning dump name all dump ids less than 210, else raising DumpNotFoundException """
    if dump_id < 210:
        return f"listenbrainz-spark-dump-{dump_id}-incremental.tar"
    else:
        raise DumpNotFoundException("Dump Not Found")


def mock_import_dump_to_hdfs_error(loader: ListenbrainzDumpLoader, dump_id: int):
    """ Mock function returning dump name all dump ids less than 210, else raise DumpInvalidException"""
    if (dump_id < 210) or (210 < dump_id < 213):
        return f"listenbrainz-spark-dump-{dump_id}-incremental.tar"
    elif dump_id == 210:
        raise DumpInvalidException("Invalid Dump")
    else:
        raise DumpNotFoundException("Dump not found")


def mock_search_dump(dump_id: int, dump_type: str, imported_at: datetime):
    """ Mock function which returns True for all IDs not divisible by 3, else returns False """
    return dump_id % 3 != 0


class DumpImporterJobTestCase(SparkNewTestCase):

    def tearDown(self):
        super().tearDown()
        self.delete_uploaded_listens()
        path_found = path_exists(IMPORT_METADATA)
        if path_found:
            delete_dir(IMPORT_METADATA, recursive=True)

    def test_import_full_dump_to_hdfs(self):
        import_full_dump_to_hdfs(self.dump_loader, 1)
        self.assertEqual(1, read_files_from_HDFS(IMPORT_METADATA) \
            .filter("dump_id == 1 AND dump_type == 'full'") \
            .count())
        self.assertEqual(68, get_listens_from_dump().count())

    def test_import_incremental_dump_to_hdfs(self):
        import_incremental_dump_to_hdfs(self.dump_loader, 2)
        self.assertEqual(1, read_files_from_HDFS(IMPORT_METADATA) \
            .filter("dump_id == 2 AND dump_type == 'incremental'") \
            .count())
        self.assertEqual(9, get_listens_from_dump().count())

        import_incremental_dump_to_hdfs(self.dump_loader, 3)
        self.assertEqual(1, read_files_from_HDFS(IMPORT_METADATA) \
            .filter("dump_id == 3 AND dump_type == 'incremental'") \
            .count())
        self.assertEqual(17, get_listens_from_dump().count())

    def test_import_incremental_dump_to_hdfs_after_full_dump(self):
        import_full_dump_to_hdfs(self.dump_loader, 1)
        import_incremental_dump_to_hdfs(self.dump_loader, 2)
        import_incremental_dump_to_hdfs(self.dump_loader, 3)
        self.assertEqual(3, read_files_from_HDFS(IMPORT_METADATA).count())
        self.assertEqual(85, get_listens_from_dump().count())

    @patch("ftplib.FTP")
    @patch.object(ListenBrainzFtpDumpLoader, "load_listens")
    @patch("listenbrainz_spark.listens.dump.upload_archive_to_hdfs_temp")
    @patch("listenbrainz_spark.listens.dump.process_full_listens_dump")
    @patch("listenbrainz_spark.listens.dump.datetime")
    def test_import_full_dump_handler(self, mock_datetime, _, mock_upload, mock_download, __):
        mock_src = MagicMock()
        mock_download.return_value = (mock_src, "listenbrainz-spark-dump-202-20200915-180002-full.tar", 202)
        mock_datetime.now.return_value = datetime(2020, 8, 18, tzinfo=timezone.utc)

        messages = import_full_dump_handler(dump_id=None, local=False)
        mock_download.assert_called_once_with(directory=mock.ANY, dump_type=DumpType.FULL, listens_dump_id=None)
        mock_upload.assert_called_once_with(mock_src, ".parquet")

        # Check if appropriate entry has been made in the table
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
        expected_count = import_meta_df \
            .filter("dump_id == 202 AND dump_type == 'full'") \
            .count()

        self.assertEqual(expected_count, 1)
        self.assertEqual(len(messages), 1)
        self.assertListEqual(
            ["listenbrainz-spark-dump-202-20200915-180002-full.tar"],
            messages[0]["imported_dump"]
        )

    @patch("ftplib.FTP")
    @patch.object(ListenBrainzFtpDumpLoader, "load_listens")
    @patch("listenbrainz_spark.listens.dump.upload_archive_to_hdfs_temp")
    @patch("listenbrainz_spark.listens.dump.process_full_listens_dump")
    @patch("listenbrainz_spark.listens.dump.datetime")
    def test_import_full_dump_handler_dump_id(self, mock_datetime, _, mock_upload, mock_download, __):
        mock_src = MagicMock()
        mock_download.return_value = (mock_src, "listenbrainz-spark-dump-202-20200915-180002-full.tar", 202)
        mock_datetime.now.return_value = datetime(2020, 8, 18)

        messages = import_full_dump_handler(202, local=False)
        mock_download.assert_called_once_with(directory=mock.ANY, dump_type=DumpType.FULL, listens_dump_id=202)
        mock_upload.assert_called_once_with(mock_src, ".parquet")

        # Check if appropriate entry has been made in the table
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
        expected_count = import_meta_df \
            .filter(import_meta_df.imported_at == datetime(2020, 8, 18)) \
            .filter("dump_id == 202 AND dump_type == 'full'") \
            .count()

        self.assertEqual(expected_count, 1)
        self.assertEqual(len(messages), 1)
        self.assertListEqual(["listenbrainz-spark-dump-202-20200915-180002-full.tar"], messages[0]["imported_dump"])

    @patch("ftplib.FTP")
    @patch.object(ListenBrainzFtpDumpLoader, "get_latest_dump_id", return_value=210)
    @patch("listenbrainz_spark.listens.dump.import_incremental_dump_to_hdfs", side_effect=mock_import_dump_to_hdfs)
    @patch("listenbrainz_spark.listens.dump.search_dump", side_effect=mock_search_dump)
    @patch("listenbrainz_spark.listens.dump.get_latest_full_dump")
    def test_import_incremental_dump_handler(self, mock_latest_full_dump, _, mock_import_dump, __, ___):
        """ Test to make sure required incremental dumps are imported. """
        mock_latest_full_dump.return_value = {
            "dump_id": 202,
            "imported_at": datetime(2020, 9, 29),
            "dump_type": DumpType.FULL
        }
        mock_import_calls = []
        expected_import_list = []
        for dump_id in range(204, 210, 3):
            mock_import_calls.append(call(mock.ANY, dump_id=dump_id))
            expected_import_list.append(f"listenbrainz-spark-dump-{dump_id}-incremental.tar")

        messages = import_incremental_dump_handler(local=False)

        mock_import_dump.assert_has_calls(mock_import_calls)
        self.assertListEqual(expected_import_list, messages[0]["imported_dump"])

    @patch("ftplib.FTP")
    @patch.object(ListenBrainzFtpDumpLoader, "get_latest_dump_id", return_value=210)
    @patch("listenbrainz_spark.listens.dump.import_incremental_dump_to_hdfs", side_effect=mock_import_dump_to_hdfs_error)
    @patch("listenbrainz_spark.listens.dump.search_dump", side_effect=mock_search_dump)
    @patch("listenbrainz_spark.listens.dump.get_latest_full_dump")
    def test_import_incremental_dump_handler_error(self, mock_latest_full_dump, _, mock_import_dump, __, ___):
        """ Test to make sure import continues if there is a fatal error. """
        mock_latest_full_dump.return_value = {
            "dump_id": 202,
            "imported_at": datetime(2020, 9, 29),
            "dump_type": "incremental"
        }
        mock_import_calls = []
        expected_import_list = []
        for dump_id in range(204, 210, 3):
            mock_import_calls.append(call(mock.ANY, dump_id=dump_id))
            expected_import_list.append(f"listenbrainz-spark-dump-{dump_id}-incremental.tar")

        messages = import_incremental_dump_handler(local=False)

        mock_import_dump.assert_has_calls(mock_import_calls)
        # Only three calls should be made
        self.assertEqual(mock_import_dump.call_count, 3)
        self.assertListEqual(expected_import_list, messages[0]["imported_dump"])

    @patch("listenbrainz_spark.listens.dump.import_incremental_dump_to_hdfs")
    @patch("listenbrainz_spark.listens.dump.get_latest_full_dump", return_value=None)
    def test_import_incremental_dump_handler_no_full_dump(self, _, mock_import_dump):
        """ Test to make sure only latest incremental dump is imported if no full dump is found """
        mock_import_dump.return_value = 'listenbrainz-spark-dump-202-20200915-180002-incremental.tar'

        messages = import_incremental_dump_handler(local=False)

        mock_import_dump.assert_called_once_with(mock.ANY, dump_id=None)
        self.assertEqual(len(messages), 1)
        self.assertListEqual(["listenbrainz-spark-dump-202-20200915-180002-incremental.tar"],
                             messages[0]["imported_dump"])

    @patch("ftplib.FTP")
    @patch.object(ListenBrainzFtpDumpLoader, "load_listens")
    @patch("listenbrainz_spark.listens.dump.upload_archive_to_hdfs_temp")
    @patch("listenbrainz_spark.listens.dump.process_incremental_listens_dump")
    @patch("listenbrainz_spark.listens.dump.datetime")
    def test_import_incremental_dump_handler_dump_id(self, mock_datetime, __, mock_upload, mock_download, _):
        mock_src = MagicMock()
        mock_download.return_value = (mock_src, "listenbrainz-spark-dump-202-20200915-180002-incremental.tar", 202)
        mock_datetime.now.return_value = datetime(2020, 8, 18)

        messages = import_incremental_dump_handler(202, local=False)
        mock_download.assert_called_once_with(directory=mock.ANY, listens_dump_id=202, dump_type=DumpType.INCREMENTAL)
        mock_upload.assert_called_once_with(mock_src, ".parquet")

        # Check if appropriate entry has been made in the table
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
        expected_count = import_meta_df \
            .filter(import_meta_df.imported_at == datetime(2020, 8, 18)) \
            .filter("dump_id == 202 AND dump_type == 'incremental'") \
            .count()

        self.assertEqual(expected_count, 1)
        self.assertEqual(len(messages), 1)
        self.assertListEqual(['listenbrainz-spark-dump-202-20200915-180002-incremental.tar'],
                             messages[0]['imported_dump'])
