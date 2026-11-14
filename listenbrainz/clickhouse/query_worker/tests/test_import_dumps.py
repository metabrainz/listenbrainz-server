from listenbrainz.clickhouse.query_worker.listens.ftp import DumpNotFoundException, DumpType
from listenbrainz.clickhouse.query_worker.listens.import_state import INCREMENTAL_DUMP_STATE, get_import_state
from listenbrainz.clickhouse.query_worker.listens.load_dump import (
    import_full_dump,
    import_missing_incremental_dumps,
)
from listenbrainz.clickhouse.query_worker.tests import ClickHouseTestCase, fixture_listens
from listenbrainz.clickhouse.query_worker.tests.ftp_server import DumpFTPServer


class ImportDumpsTestCase(ClickHouseTestCase):
    """Imports from a real FTP server into a real ClickHouse database."""

    def setUp(self):
        super().setUp()
        self.ftp = DumpFTPServer(self)
        self.downloader = self.ftp.downloader()

    def mark(self):
        return get_import_state(self.client, INCREMENTAL_DUMP_STATE)

    def import_full(self, **kwargs):
        return import_full_dump(self.connection, self.downloader, workers=2, **kwargs)

    def catch_up(self, **kwargs):
        return import_missing_incremental_dumps(self.connection, self.downloader, workers=2, **kwargs)

    def test_catch_up_needs_a_full_dump(self):
        self.ftp.add_dump(2, DumpType.INCREMENTAL, "incremental-dump-2")
        with self.assertRaisesRegex(RuntimeError, "No full dump imported"):
            self.catch_up()
        self.assertEqual(self.listens(), [])

    def test_full_dump_then_incremental_catch_up(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.INCREMENTAL, "incremental-dump-2")
        self.ftp.add_dump(3, DumpType.INCREMENTAL, "incremental-dump-3")

        result = self.import_full()
        self.assertEqual((result["dump_id"], result["errors"]), (1, []))
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1"))
        self.assertEqual(self.mark(), 1)

        result = self.catch_up(max_dumps=1)
        self.assertEqual([dump["dump_id"] for dump in result["imported"]], [2])
        self.assertEqual((result["pending"], result["errors"]), (1, []))
        self.assertEqual(self.mark(), 2)

        result = self.catch_up()
        self.assertEqual([dump["dump_id"] for dump in result["imported"]], [3])
        self.assertEqual(result["pending"], 0)
        self.assertEqual(self.mark(), 3)
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1", "incremental-dump-2", "incremental-dump-3"))
        self.assertEqual(self.staging_tables(), [])

        self.assertEqual(self.catch_up()["imported"], [])

    def test_each_imported_dump_reports_the_dumps_pending_after_it(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.INCREMENTAL, "incremental-dump-2")
        self.ftp.add_dump(3, DumpType.INCREMENTAL, "incremental-dump-3")
        self.ftp.add_dump(4, DumpType.INCREMENTAL, "incremental-dump-3")
        self.import_full()
        result = self.catch_up()
        self.assertEqual([(dump["dump_id"], dump["pending"]) for dump in result["imported"]], [(2, 2), (3, 1), (4, 0)])
        # dump 4 repeats dump 3: its listens are all there already
        self.assertEqual([dump["added"] > 0 for dump in result["imported"]], [True, True, False])

    def test_catch_up_stops_at_a_failed_dump(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.INCREMENTAL, "incremental-dump-2", checksum="wrong")
        self.ftp.add_dump(3, DumpType.INCREMENTAL, "incremental-dump-3")
        self.import_full()

        result = self.catch_up()
        self.assertEqual(result["imported"], [])
        self.assertEqual([dump_id for dump_id, _ in result["errors"]], [2])
        self.assertEqual(result["pending"], 2)
        self.assertEqual(self.mark(), 1)
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1"))

    def test_max_dumps_must_be_positive(self):
        for max_dumps in (0, -1):
            with self.subTest(max_dumps=max_dumps), self.assertRaises(ValueError):
                self.catch_up(max_dumps=max_dumps)

    def test_expired_incremental_is_rejected_without_advancing(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(3, DumpType.INCREMENTAL, "incremental-dump-3")
        self.import_full()
        before = self.listens()
        result = self.catch_up()
        self.assertIn("coverage gap", result["errors"][0][1])
        self.assertEqual(result["imported"], [])
        self.assertEqual(self.mark(), 1)
        self.assertEqual(self.listens(), before)

    def test_gap_in_middle_stops_at_last_complete_dump(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.INCREMENTAL, "incremental-dump-2")
        self.ftp.add_dump(4, DumpType.INCREMENTAL, "incremental-dump-3")
        self.import_full()
        result = self.catch_up()
        self.assertEqual([dump["dump_id"] for dump in result["imported"]], [2])
        self.assertIn("coverage gap", result["errors"][0][1])
        self.assertEqual(self.mark(), 2)

    def test_incremental_without_listens_advances_the_mark(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.INCREMENTAL, None)
        self.ftp.add_dump(3, DumpType.INCREMENTAL, "incremental-dump-3")
        self.import_full()
        result = self.catch_up()
        self.assertEqual(([dump["dump_id"] for dump in result["imported"]], result["errors"]), ([2, 3], []))
        self.assertEqual(self.mark(), 3)
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1", "incremental-dump-3"))

    def test_full_dump_without_listens_is_rejected(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.import_full()
        self.ftp.add_dump(2, DumpType.FULL, None)
        with self.assertRaisesRegex(ValueError, "no Parquet files"):
            self.import_full()
        self.assertEqual(self.mark(), 1)
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1"))

    def test_full_dump_clears_the_mark_before_swapping_in_listens(self):
        # so a failure from the swap on leaves no mark from the previous listens
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.import_full()
        self.client.command("SYSTEM FLUSH LOGS")
        rows = self.client.query(
            """
            SELECT type, query FROM system.query_log
             WHERE current_database = currentDatabase()
               AND type IN ('QueryStart', 'QueryFinish')
               AND (query LIKE '%INSERT INTO import_state%' OR query LIKE 'EXCHANGE TABLES%')
             ORDER BY event_time_microseconds, type
            """
        ).result_rows
        steps = [(kind, "exchange" if query.startswith("EXCHANGE") else "mark") for kind, query in rows]
        self.assertEqual(steps[:4], [
            ("QueryStart", "mark"), ("QueryFinish", "mark"), ("QueryStart", "exchange"), ("QueryFinish", "exchange"),
        ])

    def test_nonconsecutive_ids_with_continuous_coverage(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(5, DumpType.INCREMENTAL, "incremental-dump-2", coverage_day=2)
        self.import_full()
        self.assertEqual(self.catch_up()["errors"], [])
        self.assertEqual(self.mark(), 5)

    def test_selected_full_dump_replaces_newer_import(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.FULL, "incremental-dump-2")
        self.import_full()
        self.assertEqual(self.mark(), 2)
        result = self.import_full(dump_id=1)
        self.assertEqual(result["dump_id"], 1)
        self.assertEqual(self.mark(), 1)
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1"))

    def test_selected_incremental_and_replay_preserve_progress(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.INCREMENTAL, "incremental-dump-2")
        self.ftp.add_dump(3, DumpType.INCREMENTAL, "incremental-dump-3")
        self.ftp.add_dump(4, DumpType.INCREMENTAL, "incremental-dump-3")
        self.import_full()
        result = self.catch_up(dump_id=2)
        self.assertEqual([dump["dump_id"] for dump in result["imported"]], [2])
        self.assertEqual(result["pending"], 2)
        self.catch_up(dump_id=3)
        before = self.listens()
        result = self.catch_up(dump_id=2)
        self.assertEqual(result["imported"][0]["added"], 0)
        self.assertEqual(result["pending"], 1)
        self.assertEqual(self.mark(), 3)
        self.assertEqual(self.listens(), before)
        self.assertEqual(self.catch_up()["errors"], [])
        self.assertEqual(self.mark(), 4)

    def test_selected_incremental_cannot_skip_coverage(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.INCREMENTAL, "incremental-dump-2")
        self.ftp.add_dump(3, DumpType.INCREMENTAL, "incremental-dump-3")
        self.import_full()
        result = self.catch_up(dump_id=3)
        self.assertIn("coverage gap", result["errors"][0][1])
        self.assertEqual(result["pending"], 2)
        self.assertEqual(self.mark(), 1)

    def test_unknown_selected_dump_fails(self):
        self.ftp.add_dump(1, DumpType.FULL, "full-dump-1")
        self.ftp.add_dump(2, DumpType.INCREMENTAL, "incremental-dump-2")
        self.import_full()
        with self.assertRaises(DumpNotFoundException):
            self.import_full(dump_id=99)
        with self.assertRaises(DumpNotFoundException):
            self.catch_up(dump_id=99)
        self.assertEqual(self.mark(), 1)

    def test_selected_dump_and_limit_are_mutually_exclusive(self):
        with self.assertRaisesRegex(ValueError, "cannot be used together"):
            self.catch_up(dump_id=2, max_dumps=1)
