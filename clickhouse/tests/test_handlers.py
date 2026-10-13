from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from clickhouse.stats import handlers
from clickhouse.tests import ClickHouseTestCase, TEST_DATA_PATH
from clickhouse.stats.import_state import INCREMENTAL_DUMP_STATE, get_import_state


class DatabaseHandlerTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        settings = self.config_settings()
        patcher = mock.patch.multiple(handlers.config, **settings)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_set_dump_import_state(self):
        self.assertEqual(handlers.set_dump_import_state(2560), [
            {"type": "clk_dump_import_state_set", "status": "success", "dump_id": 2560},
        ])
        self.assertEqual(get_import_state(self.client, INCREMENTAL_DUMP_STATE), 2560)

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
