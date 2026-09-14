import unittest
from unittest import mock

from clickhouse.stats.ftp import DumpNotFoundException, DumpType, FTPDumpDownloader


class FTPDumpDownloaderTestCase(unittest.TestCase):

    def test_get_spark_dump_filename(self):
        downloader = FTPDumpDownloader()

        self.assertEqual(
            downloader.get_spark_dump_filename("listenbrainz-dump-17-20190101-000001-full/"),
            "listenbrainz-spark-dump-17-20190101-000001-full.tar",
        )
        self.assertEqual(
            downloader.get_spark_dump_filename("listenbrainz-dump-17-20190101-000001-incremental"),
            "listenbrainz-spark-dump-17-20190101-000001-incremental.tar",
        )

    def test_list_dump_directories_drops_database_dumps(self):
        downloader = FTPDumpDownloader()
        downloader.connection = mock.Mock()
        downloader.list_dir = mock.Mock(return_value=[
            "listenbrainz-dump-2534-20260524-000003-full/",
            "listenbrainz-dump-2535-20260525-000001-db/",
        ])

        self.assertEqual(
            downloader.list_dump_directories(DumpType.FULL),
            ["listenbrainz-dump-2534-20260524-000003-full/"],
        )

    def test_list_dump_ids_sorts_and_skips_unrecognised_names(self):
        downloader = FTPDumpDownloader()
        downloader.list_dump_directories = mock.Mock(return_value=[
            "listenbrainz-dump-2536-20260526-000003-incremental",
            "listenbrainz-dump-2534-20260524-000003-incremental",
            "index.html",
        ])

        self.assertEqual(downloader.list_dump_ids(DumpType.INCREMENTAL), [
            (2534, "listenbrainz-dump-2534-20260524-000003-incremental"),
            (2536, "listenbrainz-dump-2536-20260526-000003-incremental"),
        ])

    def test_get_dump_name_defaults_to_latest(self):
        downloader = FTPDumpDownloader()
        downloader.list_dump_ids = mock.Mock(return_value=[
            (2534, "listenbrainz-dump-2534-20260524-000003-incremental"),
            (2536, "listenbrainz-dump-2536-20260526-000003-incremental"),
        ])

        self.assertEqual(
            downloader.get_dump_name(DumpType.INCREMENTAL),
            ("listenbrainz-dump-2536-20260526-000003-incremental", 2536),
        )

    def test_get_dump_name_finds_a_specific_dump(self):
        downloader = FTPDumpDownloader()
        downloader.list_dump_ids = mock.Mock(return_value=[
            (2534, "listenbrainz-dump-2534-20260524-000003-incremental"),
            (2536, "listenbrainz-dump-2536-20260526-000003-incremental"),
        ])

        self.assertEqual(
            downloader.get_dump_name(DumpType.INCREMENTAL, 2534),
            ("listenbrainz-dump-2534-20260524-000003-incremental", 2534),
        )
        with self.assertRaises(DumpNotFoundException):
            downloader.get_dump_name(DumpType.INCREMENTAL, 2535)

    def test_download_dump_archive_downloads_spark_archive(self):
        downloader = FTPDumpDownloader()
        downloader.connection = mock.Mock()
        downloader.get_dump_name = mock.Mock(
            return_value=("listenbrainz-dump-2534-20260524-000003-incremental", 2534)
        )
        downloader.download_dump = mock.Mock(return_value="/tmp/listenbrainz-spark-dump.tar")

        archive_path, dump_id = downloader.download_dump_archive(DumpType.INCREMENTAL, "/tmp")

        self.assertEqual(archive_path, "/tmp/listenbrainz-spark-dump.tar")
        self.assertEqual(dump_id, 2534)
        downloader.get_dump_name.assert_called_once_with(DumpType.INCREMENTAL, None)
        downloader.connection.cwd.assert_has_calls([
            mock.call("listenbrainz-dump-2534-20260524-000003-incremental"),
            mock.call("/"),
        ])
        downloader.download_dump.assert_called_once_with(
            "listenbrainz-spark-dump-2534-20260524-000003-incremental.tar",
            "/tmp",
        )

    def test_download_dump_archive_passes_the_requested_dump_id(self):
        downloader = FTPDumpDownloader()
        downloader.connection = mock.Mock()
        downloader.get_dump_name = mock.Mock(
            return_value=("listenbrainz-dump-2534-20260524-000003-incremental", 2534)
        )
        downloader.download_dump = mock.Mock(return_value="/tmp/listenbrainz-spark-dump.tar")

        downloader.download_dump_archive(DumpType.INCREMENTAL, "/tmp", 2534)

        downloader.get_dump_name.assert_called_once_with(DumpType.INCREMENTAL, 2534)


if __name__ == "__main__":
    unittest.main()
