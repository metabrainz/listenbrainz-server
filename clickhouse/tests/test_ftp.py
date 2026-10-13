import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from clickhouse.stats.ftp import DumpInvalidException, DumpNotFoundException, DumpType, FTPDumpDownloader
from clickhouse.tests import TEST_DATA_PATH


class FTPDumpDownloaderTestCase(unittest.TestCase):
    def setUp(self):
        self.downloader = FTPDumpDownloader()
        # Only the FTP transport is replaced. Directory parsing, file writes and
        # checksum validation run normally, using bytes from a real dump fixture.
        self.downloader.connection = mock.Mock()
        self.names = [
            "listenbrainz-dump-2536-20260526-000003-incremental",
            "listenbrainz-dump-2534-20260524-000003-incremental",
            "index.html",
            "listenbrainz-dump-invalid-20260524-000003-incremental",
        ]
        self.downloader.connection.retrlines.side_effect = self.listing

    def listing(self, command, callback):
        for name in self.names:
            callback(name)

    def test_list_dump_ids_sorts_and_ignores_invalid_directories(self):
        self.assertEqual(self.downloader.list_dump_ids(DumpType.INCREMENTAL), [
            (2534, "listenbrainz-dump-2534-20260524-000003-incremental"),
            (2536, "listenbrainz-dump-2536-20260526-000003-incremental"),
        ])

    def test_full_dump_listing_excludes_database_dumps(self):
        self.names = ["listenbrainz-dump-1-20260524-000003-full/", "listenbrainz-dump-2-20260524-000003-db/"]
        self.assertEqual(self.downloader.list_dump_ids(DumpType.FULL), [(1, self.names[0])])

    def test_selects_latest_or_requested_dump(self):
        self.assertEqual(self.downloader.get_dump_name(DumpType.INCREMENTAL)[1], 2536)
        self.assertEqual(self.downloader.get_dump_name(DumpType.INCREMENTAL, 2534)[1], 2534)
        with self.assertRaises(DumpNotFoundException):
            self.downloader.get_dump_name(DumpType.INCREMENTAL, 2535)
        self.names = []
        with self.assertRaisesRegex(ValueError, "No incremental dumps"):
            self.downloader.get_dump_name(DumpType.INCREMENTAL)

    def prepare_download(self, corrupt=False, checksum=True):
        content = (TEST_DATA_PATH / "incremental-dump-2" / "0.parquet").read_bytes()
        filename = "listenbrainz-spark-dump-2534-20260524-000003-incremental.tar"
        files = {filename: content}
        if checksum:
            digest = "0" * 64 if corrupt else hashlib.sha256(content).hexdigest()
            files[filename + ".sha256"] = f"{digest}  {filename}\n".encode()
        self.downloader.connection.retrlines.side_effect = lambda command, callback: [callback(name) for name in files]

        def download(command, callback):
            data = files[command.removeprefix("RETR ")]
            for offset in range(0, len(data), 1024):
                callback(data[offset:offset + 1024])

        self.downloader.connection.retrbinary.side_effect = download
        return filename, content

    def test_download_writes_fixture_bytes_and_validates_checksum(self):
        filename, content = self.prepare_download()
        with TemporaryDirectory() as tmp:
            path = self.downloader.download_dump(filename, tmp)
            self.assertEqual(Path(path).read_bytes(), content)
            self.assertEqual(list(Path(tmp).iterdir()), [Path(path)])

    def test_invalid_checksum_removes_corrupt_download(self):
        filename, _ = self.prepare_download(corrupt=True)
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(DumpInvalidException, "SHA256 mismatch"):
                self.downloader.download_dump(filename, tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_missing_checksum_does_not_download(self):
        filename, _ = self.prepare_download(checksum=False)
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(DumpInvalidException, "checksum file not found"):
                self.downloader.download_dump(filename, tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_archive_selection_downloads_requested_file(self):
        filename, content = self.prepare_download()
        names = self.names
        listings = iter((names, [filename, filename + ".sha256"]))
        self.downloader.connection.retrlines.side_effect = lambda command, callback: [callback(name) for name in next(listings)]
        with TemporaryDirectory() as tmp:
            path, dump_id = self.downloader.download_dump_archive(DumpType.INCREMENTAL, tmp, 2534)
            self.assertEqual(dump_id, 2534)
            self.assertEqual(Path(path).name, filename)
            self.assertEqual(Path(path).read_bytes(), content)
