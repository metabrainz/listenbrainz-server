import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from listenbrainz.clickhouse.query_worker.listens.ftp import DumpInvalidException, DumpNotFoundException, DumpType
from listenbrainz.clickhouse.query_worker.tests.ftp_server import DumpFTPServer, dump_dir_name


class FTPDumpDownloaderTestCase(unittest.TestCase):
    def setUp(self):
        self.ftp = DumpFTPServer(self)

    def test_list_dump_ids_sorts_and_ignores_invalid_directories(self):
        self.ftp.add_dump(2536, DumpType.INCREMENTAL, "incremental-dump-3")
        self.ftp.add_dump(2534, DumpType.INCREMENTAL, "incremental-dump-2")
        incremental = self.ftp.dump_dir(DumpType.INCREMENTAL)
        (incremental / "index.html").write_text("")
        (incremental / "listenbrainz-dump-invalid-20260524-000003-incremental").mkdir()
        with self.ftp.downloader() as downloader:
            self.assertEqual(downloader.list_dump_ids(DumpType.INCREMENTAL), [
                (2534, dump_dir_name(2534, DumpType.INCREMENTAL)),
                (2536, dump_dir_name(2536, DumpType.INCREMENTAL)),
            ])

    def test_full_dump_listing_excludes_database_dumps(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        (self.ftp.dump_dir(DumpType.FULL) / dump_dir_name(2, "db")).mkdir()
        with self.ftp.downloader() as downloader:
            self.assertEqual(downloader.list_dump_ids(DumpType.FULL), [(1, dump_dir_name(1, DumpType.FULL))])

    def test_selects_latest_or_requested_dump(self):
        self.ftp.dump_dir(DumpType.INCREMENTAL)
        with self.ftp.downloader() as downloader:
            with self.assertRaisesRegex(ValueError, "No incremental dumps"):
                downloader.get_dump_name(DumpType.INCREMENTAL)
            self.ftp.add_dump(2534, DumpType.INCREMENTAL, "incremental-dump-2")
            self.ftp.add_dump(2536, DumpType.INCREMENTAL, "incremental-dump-3")
            self.assertEqual(downloader.get_dump_name(DumpType.INCREMENTAL)[1], 2536)
            self.assertEqual(downloader.get_dump_name(DumpType.INCREMENTAL, 2534)[1], 2534)
            with self.assertRaises(DumpNotFoundException):
                downloader.get_dump_name(DumpType.INCREMENTAL, 2535)

    def test_download_verifies_checksum(self):
        archive = self.ftp.add_dump(2534, DumpType.INCREMENTAL, "incremental-dump-2")
        self.ftp.dump_dir(DumpType.FULL)
        with TemporaryDirectory() as download_dir, self.ftp.downloader() as downloader:
            # after a listing, which leaves the connection in another directory
            downloader.list_dump_ids(DumpType.FULL)
            path = downloader.download_spark_archive(
                DumpType.INCREMENTAL, dump_dir_name(2534, DumpType.INCREMENTAL), download_dir,
            )
            self.assertEqual(Path(path).read_bytes(), archive.read_bytes())
            self.assertEqual(os.listdir(download_dir), [archive.name])

    def test_invalid_checksum_removes_corrupt_download(self):
        self.ftp.add_dump(2534, DumpType.INCREMENTAL, "incremental-dump-2", checksum="wrong")
        with (
            TemporaryDirectory() as download_dir,
            self.ftp.downloader() as downloader,
        ):
            with self.assertRaisesRegex(DumpInvalidException, "SHA256 mismatch"):
                downloader.download_spark_archive(
                    DumpType.INCREMENTAL,
                    dump_dir_name(2534, DumpType.INCREMENTAL), download_dir,
                )
            self.assertEqual(os.listdir(download_dir), [])

    def test_missing_checksum_does_not_download(self):
        self.ftp.add_dump(2534, DumpType.INCREMENTAL, "incremental-dump-2", checksum=None)
        with (
            TemporaryDirectory() as download_dir,
            self.ftp.downloader() as downloader,
        ):
            with self.assertRaisesRegex(DumpInvalidException, "checksum file not found"):
                downloader.download_spark_archive(
                    DumpType.INCREMENTAL,
                    dump_dir_name(2534, DumpType.INCREMENTAL), download_dir,
                )
            self.assertEqual(os.listdir(download_dir), [])
