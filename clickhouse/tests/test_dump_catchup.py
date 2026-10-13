import io
import tarfile
from pathlib import Path
from unittest import mock

from clickhouse.stats.ftp import DumpType
from clickhouse.stats import handlers
from clickhouse.stats.imported_dumps import get_incremental_dumps_since_latest_full, get_latest_full_dump
from clickhouse.stats.load_dump import import_missing_incremental_dumps, load_from_ftp
from clickhouse.tests import ClickHouseTestCase, TEST_DATA_PATH


class DumpCatchupTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        # Replace only the FTP boundary. Extraction, Parquet ingestion, deduplication,
        # import history and catch-up selection all execute production code.
        patcher = mock.patch("clickhouse.stats.load_dump.FTPDumpDownloader", autospec=True)
        downloader = patcher.start().return_value
        self.addCleanup(patcher.stop)
        downloader.__enter__.return_value = downloader
        downloader.list_dump_ids.return_value = [(i, f"incremental-dump-{i}") for i in (1, 2, 3)]
        downloader.download_dump_archive.side_effect = self.archive
        self.corrupt = None
        self.unavailable = None
        self.downloads = []

    def archive(self, dump_type, directory, dump_id):
        dump_id = dump_id or (1 if dump_type == DumpType.FULL else 3)
        self.downloads.append(dump_id)
        if dump_id == self.unavailable:
            raise TimeoutError("FTP timed out")
        path = Path(directory) / "dump.tar"
        with tarfile.open(path, "w") as archive:
            if dump_id == self.corrupt:
                data = b"broken parquet"
                info = tarfile.TarInfo("dump/broken.parquet")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            else:
                archive.add(TEST_DATA_PATH / f"{dump_type.value}-dump-{dump_id}", arcname="dump")
        return str(path), dump_id

    def full_import(self):
        result = load_from_ftp(DumpType.FULL, self.connection, replace=True)
        self.assertEqual(result["errors"], [])
        self.assertEqual(get_latest_full_dump(self.client)["dump_id"], 1)
        return self.client.query("SELECT count() FROM listens").first_row[0]

    def test_catchup_imports_in_order_and_resumes_with_limit(self):
        before = self.full_import()
        first = import_missing_incremental_dumps(self.connection, max_dumps=1)
        self.assertEqual([d["dump_id"] for d in first["imported"]], [2])
        self.assertEqual(first["pending"], 1)
        second = import_missing_incremental_dumps(self.connection)
        self.assertEqual([d["dump_id"] for d in second["imported"]], [3])
        self.assertEqual(second["pending"], 0)
        self.assertEqual(self.downloads, [1, 2, 3])
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), {2, 3})
        self.assertGreater(self.client.query("SELECT count() FROM listens").first_row[0], before)
        self.assertEqual(import_missing_incremental_dumps(self.connection)["imported"], [])
        self.assertEqual(self.downloads, [1, 2, 3])

    def test_corrupt_dump_is_not_recorded_or_skipped_and_can_be_retried(self):
        before = self.full_import()
        self.corrupt = 2
        failed = import_missing_incremental_dumps(self.connection)
        self.assertEqual(failed["imported"], [])
        self.assertEqual(failed["errors"][0][0], 2)
        self.assertEqual(failed["pending"], 2)
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), set())
        self.assertEqual(self.client.query("SELECT count() FROM listens").first_row[0], before)
        self.assertEqual(self.downloads, [1, 2])
        self.corrupt = None
        retried = import_missing_incremental_dumps(self.connection)
        self.assertEqual([d["dump_id"] for d in retried["imported"]], [2, 3])
        self.assertEqual(retried["errors"], [])

    def test_network_failure_stops_before_later_dumps(self):
        self.full_import()
        self.unavailable = 2
        result = import_missing_incremental_dumps(self.connection)
        self.assertEqual(result["errors"], [(2, "FTP timed out")])
        self.assertEqual(self.downloads, [1, 2])
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), set())

    def test_without_full_import_only_latest_is_loaded_once(self):
        result = import_missing_incremental_dumps(self.connection)
        self.assertEqual([d["dump_id"] for d in result["imported"]], [3])
        self.assertGreater(self.client.query("SELECT count() FROM listens").first_row[0], 0)
        self.assertEqual(import_missing_incremental_dumps(self.connection)["imported"], [])
        self.assertEqual(self.downloads, [3])

    def test_import_handlers_report_loaded_dumps_and_errors(self):
        settings = self.config_settings()
        with mock.patch.multiple(handlers.config, **settings):
            full = handlers.import_full_dump()
            self.assertEqual(full[0]["status"], "success")
            self.assertTrue(full[0]["replace"])
            self.corrupt = 2
            failure = handlers.import_incremental_dump()
            self.assertEqual(failure[0]["status"], "error")
            self.assertEqual(failure[0]["dump_id"], 2)
            self.assertEqual(failure[0]["pending"], 2)
            self.corrupt = None
            first = handlers.import_incremental_dump(max_dumps=1)
            self.assertEqual([m["dump_id"] for m in first], [2])
            second = handlers.import_incremental_dump()
            self.assertEqual([m["dump_id"] for m in second], [3])
            self.assertTrue(all(m["status"] == "success" and not m["replace"] for m in first + second))
