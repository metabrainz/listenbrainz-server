from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from clickhouse.stats import handlers
from clickhouse.tests import ClickHouseTestCase, TEST_DATA_PATH
from clickhouse.stats.imported_dumps import get_latest_full_dump, get_incremental_dumps_since_latest_full


class DatabaseHandlerTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        settings = {"CLICKHOUSE_" + key.upper(): value for key, value in self.connection.items()}
        patcher = mock.patch.multiple(handlers.config, **settings)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_record_import_validates_input_and_persists_timestamp(self):
        messages = handlers.record_dump_import(2560, "full", "2026-06-10 00:21:48.531")
        self.assertEqual(messages[0]["status"], "success")
        self.assertEqual(get_latest_full_dump(self.client), {
            "dump_id": 2560, "imported_at": datetime(2026, 6, 10, 0, 21, 48, 531000),
        })
        self.assertEqual(handlers.record_dump_import(2633, "incremental")[0]["status"], "success")
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), {2633})
        for dump_type, imported_at in (("sample", None), ("incremental", "last tuesday")):
            self.assertEqual(handlers.record_dump_import(9999, dump_type, imported_at)[0]["status"], "error")
        self.assertEqual(self.client.query("SELECT count() FROM imported_dumps").first_row[0], 2)

    def test_schema_handler_reports_real_migration_failure(self):
        self.assertEqual(handlers.init_schema(), [{"type": "clk_schema_initialized", "status": "success"}])
        self.client.command("DROP TABLE raw_listens")
        self.client.command("CREATE TABLE raw_listens (user_id UInt32) ENGINE=MergeTree ORDER BY user_id")
        self.client.insert("raw_listens", [(1,)], column_names=["user_id"])
        result = handlers.init_schema()
        self.assertEqual(result[0]["status"], "error")
        self.assertIn("still holds 1 rows", result[0]["error"])
        self.assertEqual(self.client.query("SELECT * FROM raw_listens").result_rows, [(1,)])

    def test_load_handlers_import_files_and_report_corrupt_data(self):
        self.assertEqual(handlers.load_full_dump(str(TEST_DATA_PATH / "full-dump-1"))[0]["status"], "success")
        before = self.client.query("SELECT count() FROM listens").first_row[0]
        self.assertEqual(handlers.load_incremental_dump(str(TEST_DATA_PATH / "incremental-dump-2"))[0]["status"], "success")
        self.assertGreater(self.client.query("SELECT count() FROM listens").first_row[0], before)
        # Full dump defaults to replacement, incremental dump appends.
        handlers.load_full_dump(str(TEST_DATA_PATH / "full-dump-1"))
        self.assertEqual(self.client.query("SELECT count() FROM listens").first_row[0], before)
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "broken.parquet").write_bytes(b"broken")
            result = handlers.load_incremental_dump(tmp)
        self.assertEqual(result[0]["status"], "error")
        self.assertEqual(self.client.query("SELECT count() FROM listens").first_row[0], before)

    def test_stats_handlers_compute_both_entities_and_reuse_cache(self):
        self.load_spark_listens()
        messages = list(handlers.run_full_stats_refresh(message_batch_size=1, user_flush_size=1))
        self.assertFalse(any(m["type"] == "clk_stats_error" for m in messages), messages)
        self.assertEqual(messages[-1]["entities"], ["daily_activity", "listening_activity"])
        data = [m for m in messages if m["type"] == "clk_user_entity"]
        self.assertEqual({m["entity"] for m in data}, {"daily_activity", "listening_activity"})
        self.assertTrue(all(len(m["data"]) == 1 for m in data))
        self.assertEqual(list(handlers.run_hourly_stats_job()), [{
            "type": "clk_stats_complete", "job": "hourly", "entities": ["daily_activity", "listening_activity"],
        }])
        for job in (handlers.run_hourly_stats_job, handlers.run_full_stats_refresh):
            errors = list(job(entity="artists"))
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["type"], "clk_stats_error")
