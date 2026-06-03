import unittest
from unittest import mock

from clickhouse.stats.ftp import DumpType, FTPDumpDownloader


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

    def test_download_latest_dump_downloads_spark_archive(self):
        downloader = FTPDumpDownloader()
        downloader.connection = mock.Mock()
        downloader.get_latest_dump_name = mock.Mock(
            return_value=("listenbrainz-dump-2534-20260524-000003-incremental", 2534)
        )
        downloader.download_dump = mock.Mock(return_value="/tmp/listenbrainz-spark-dump.tar")

        archive_path, dump_id = downloader.download_latest_dump(DumpType.INCREMENTAL, "/tmp")

        self.assertEqual(archive_path, "/tmp/listenbrainz-spark-dump.tar")
        self.assertEqual(dump_id, 2534)
        downloader.connection.cwd.assert_has_calls([
            mock.call("listenbrainz-dump-2534-20260524-000003-incremental"),
            mock.call("/"),
        ])
        downloader.download_dump.assert_called_once_with(
            "listenbrainz-spark-dump-2534-20260524-000003-incremental.tar",
            "/tmp",
        )


if __name__ == "__main__":
    unittest.main()
