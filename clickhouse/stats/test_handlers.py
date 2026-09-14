import unittest
from datetime import datetime
from unittest import mock

from clickhouse.stats import handlers
from clickhouse.stats.ftp import DumpType
from clickhouse.stats.activity_cache_manager import (
    ActivityStatsCacheManager,
    BulkActivityStatsCacheManager,
)
from clickhouse.stats.cache_manager import CacheConfig


class DumpHandlerTestCase(unittest.TestCase):

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.import_missing_incremental_dumps")
    def test_import_incremental_dump_reports_load_errors(self, mock_import_missing, _mock_ch_kwargs):
        mock_import_missing.return_value = {
            "imported": [],
            "pending": 3,
            "available": 10,
            "errors": [(2534, "1 parquet file(s) failed to load: /tmp/0.parquet: too long")],
        }

        messages = handlers.import_incremental_dump()

        self.assertEqual(messages[0]["type"], "clk_dump_imported")
        self.assertEqual(messages[0]["status"], "error")
        self.assertEqual(messages[0]["dump_id"], 2534)
        self.assertEqual(messages[0]["pending"], 3)
        self.assertIn("parquet file(s) failed", messages[0]["error"])

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.load_from_ftp")
    def test_import_full_dump_replaces_by_default(self, mock_load_from_ftp, _mock_ch_kwargs):
        mock_load_from_ftp.return_value = {
            "dump_id": 1, "load_id": "abc", "total_inserted": 10, "files_completed": 1, "errors": [],
        }

        messages = handlers.import_full_dump()

        self.assertEqual(mock_load_from_ftp.call_args.kwargs["replace"], True)
        self.assertEqual(messages[0]["status"], "success")
        self.assertEqual(messages[0]["load_id"], "abc")
        self.assertTrue(messages[0]["replace"])

        handlers.import_full_dump(replace=False)
        self.assertEqual(mock_load_from_ftp.call_args.kwargs["replace"], False)

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.import_missing_incremental_dumps")
    def test_import_incremental_dump_reports_one_message_per_dump(self, mock_import_missing, _mock_ch_kwargs):
        mock_import_missing.return_value = {
            "imported": [
                {"dump_id": 2534, "load_id": "abc", "total_inserted": 10, "files_completed": 1, "errors": []},
                {"dump_id": 2535, "load_id": "def", "total_inserted": 20, "files_completed": 2, "errors": []},
            ],
            "pending": 0,
            "available": 2,
            "errors": [],
        }

        messages = handlers.import_incremental_dump()

        self.assertEqual([message["dump_id"] for message in messages], [2534, 2535])
        self.assertTrue(all(message["status"] == "success" for message in messages))
        self.assertTrue(all(message["replace"] is False for message in messages))

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.import_missing_incremental_dumps")
    def test_import_incremental_dump_passes_max_dumps(self, mock_import_missing, _mock_ch_kwargs):
        mock_import_missing.return_value = {"imported": [], "pending": 0, "available": 0, "errors": []}

        self.assertEqual(handlers.import_incremental_dump(max_dumps=5), [])
        self.assertEqual(mock_import_missing.call_args.kwargs["max_dumps"], 5)


class RecordDumpImportTestCase(unittest.TestCase):

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.ensure_stats_schema")
    @mock.patch("clickhouse.stats.handlers.record_imported_dump")
    @mock.patch("clickhouse_connect.get_client")
    def test_records_a_dump_with_its_original_import_time(self, _mock_client, mock_record, *_):
        messages = handlers.record_dump_import(2560, "full", "2026-06-10 00:21:48.531")

        self.assertEqual(messages[0]["status"], "success")
        self.assertEqual(messages[0]["dump_id"], 2560)
        self.assertEqual(
            mock_record.call_args.args[1:],
            (2560, DumpType.FULL, datetime(2026, 6, 10, 0, 21, 48, 531000)),
        )

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.ensure_stats_schema")
    @mock.patch("clickhouse.stats.handlers.record_imported_dump")
    @mock.patch("clickhouse_connect.get_client")
    def test_defaults_the_import_time_to_now(self, _mock_client, mock_record, *_):
        handlers.record_dump_import(2633, "incremental")

        self.assertIsNone(mock_record.call_args.args[3])

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.record_imported_dump")
    def test_rejects_an_unknown_dump_type(self, mock_record, _mock_ch_kwargs):
        messages = handlers.record_dump_import(2633, "sample")

        self.assertEqual(messages[0]["status"], "error")
        self.assertIn("Unknown dump type", messages[0]["error"])
        mock_record.assert_not_called()

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.record_imported_dump")
    def test_rejects_an_unparseable_import_time(self, mock_record, _mock_ch_kwargs):
        messages = handlers.record_dump_import(2633, "incremental", "last tuesday")

        self.assertEqual(messages[0]["status"], "error")
        mock_record.assert_not_called()


class DeletedListensHandlerTestCase(unittest.TestCase):

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers._import_deleted_listens", return_value={"deleted_listens_imported": 2})
    def test_import_deleted_listens(self, mock_import, _mock_ch_kwargs):
        with mock.patch("clickhouse.stats.handlers.config") as mock_config, \
                mock.patch("clickhouse_connect.get_client") as mock_get_client:
            mock_config.TIMESCALE_DSN = "postgresql://ts"
            messages = handlers.import_deleted_listens(batch_size=5)

        mock_import.assert_called_once_with("postgresql://ts", mock_get_client.return_value, batch_size=5)
        mock_get_client.return_value.close.assert_called_once()
        self.assertEqual(messages, [{
            "type": "clk_deleted_listens_imported", "status": "success", "deleted_listens_imported": 2,
        }])

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    def test_import_deleted_listens_requires_timescale_dsn(self, _mock_ch_kwargs):
        with mock.patch("clickhouse.stats.handlers.config") as mock_config:
            mock_config.TIMESCALE_DSN = ""
            messages = handlers.import_deleted_listens()
        self.assertEqual(messages[0]["status"], "error")
        self.assertIn("TIMESCALE_DSN", messages[0]["error"])


class StatsHandlerTestCase(unittest.TestCase):

    def test_activity_types_use_activity_managers(self):
        incremental = handlers._stats_manager(CacheConfig(), "daily_activity")
        full = handlers._stats_manager(CacheConfig(), "listening_activity", full=True)

        self.assertIsInstance(incremental, ActivityStatsCacheManager)
        self.assertEqual(incremental.stat_type, "daily_activity")
        self.assertIsInstance(full, BulkActivityStatsCacheManager)
        self.assertEqual(full.stat_type, "listening_activity")

    def test_only_activity_stats_are_computed(self):
        self.assertEqual(list(handlers.STAT_TYPES), ["daily_activity", "listening_activity"])

    @mock.patch("clickhouse.stats.handlers._stats_manager")
    @mock.patch("clickhouse.stats.handlers.get_cache_config", return_value=CacheConfig())
    def test_entity_stats_are_rejected(self, _mock_config, mock_manager_factory):
        for job in (handlers.run_hourly_stats_job, handlers.run_full_stats_refresh):
            with self.subTest(job=job.__name__):
                messages = list(job(entity="artists"))

                self.assertEqual(messages[0]["type"], "clk_stats_error")
                self.assertIn("Unknown entity: artists", messages[0]["error"])
                mock_manager_factory.assert_not_called()

    @mock.patch("clickhouse.stats.handlers._stats_manager")
    @mock.patch("clickhouse.stats.handlers.get_cache_config", return_value=CacheConfig())
    def test_hourly_job_includes_activity_types_by_default(self, _mock_config, mock_manager_factory):
        manager = mock.Mock()
        manager.run_hourly_job.return_value = iter(())
        mock_manager_factory.return_value = manager

        messages = list(handlers.run_hourly_stats_job())

        requested_types = [call.args[1] for call in mock_manager_factory.call_args_list]
        self.assertEqual(requested_types, ["daily_activity", "listening_activity"])
        self.assertEqual(messages[-1]["entities"], ["daily_activity", "listening_activity"])

    @mock.patch("clickhouse.stats.handlers._stats_manager")
    @mock.patch("clickhouse.stats.handlers.get_cache_config", return_value=CacheConfig())
    def test_full_activity_refresh_passes_batch_sizes(
        self, _mock_config, mock_manager_factory,
    ):
        manager = mock.Mock()
        manager.run_full_refresh.return_value = iter(())
        mock_manager_factory.return_value = manager

        list(handlers.run_full_stats_refresh(entity="daily_activity"))

        manager.run_full_refresh.assert_called_once_with(
            message_batch_size=100,
            user_flush_size=5000,
        )


class SchemaHandlerTestCase(unittest.TestCase):

    def test_ensure_stats_schema_only_creates_tables_and_drops_retired_objects(self):
        from clickhouse.stats import schema

        client = mock.Mock()
        client.query.return_value.result_rows = [("load_id",)]
        schema.ensure_stats_schema(client)
        commands = [c.args[0] for c in client.command.call_args_list]
        creates = [c for c in commands if c.strip().startswith("CREATE")]
        self.assertEqual(len(creates), len(schema.CREATE_TABLES))
        self.assertTrue(all("CREATE TABLE IF NOT EXISTS" in c for c in creates))
        self.assertFalse(any("MATERIALIZED VIEW" in c or "FUNCTION" in c for c in creates))
        # the retired entity stats views / functions are dropped, nothing else is
        drops = [c for c in commands if c.startswith("DROP")]
        self.assertEqual(drops, [
            *(f"DROP TABLE IF EXISTS {view}" for view in schema.OBSOLETE_MATERIALIZED_VIEWS),
            *(f"DROP FUNCTION IF EXISTS {function}" for function in schema.OBSOLETE_FUNCTIONS),
        ])
        # and they are dropped before raw_listens might be recreated
        self.assertLess(commands.index(drops[0]), commands.index(creates[0]))

    def test_schema_has_no_entity_stats_tables(self):
        from clickhouse.stats import schema

        statements = "\n".join(schema.CREATE_TABLES)
        for name in ("artist", "recording_id", "recording_metadata", "release", "_stats_daily"):
            self.assertNotIn(name, statements)
        listens_columns = statements.split("CREATE TABLE IF NOT EXISTS listens (")[1].split(") ENGINE")[0]
        self.assertEqual(
            [line.split()[0] for line in listens_columns.strip().splitlines()],
            ["listened_at", "created", "user_id", "recording_msid"],
        )

    def test_ensure_stats_schema_recreates_empty_unpartitioned_raw_listens(self):
        from clickhouse.stats import schema

        client = mock.Mock()
        client.query.side_effect = [
            mock.Mock(result_rows=[("",)]),        # partition_key of existing raw_listens
            mock.Mock(first_row=(0,)),             # row count
        ]
        schema.ensure_stats_schema(client)
        commands = [c.args[0] for c in client.command.call_args_list]
        self.assertIn("DROP TABLE raw_listens", commands)
        # recreated with the partition key
        recreated = [c for c in commands if "CREATE TABLE IF NOT EXISTS raw_listens" in c]
        self.assertEqual(len(recreated), 2)
        self.assertIn("PARTITION BY load_id", recreated[-1])

    def test_ensure_stats_schema_refuses_to_drop_non_empty_unpartitioned_raw_listens(self):
        from clickhouse.stats import schema

        client = mock.Mock()
        client.query.side_effect = [
            mock.Mock(result_rows=[("",)]),
            mock.Mock(first_row=(5,)),
        ]
        with self.assertRaisesRegex(RuntimeError, "TRUNCATE TABLE raw_listens"):
            schema.ensure_stats_schema(client)
        commands = [c.args[0] for c in client.command.call_args_list]
        self.assertNotIn("DROP TABLE raw_listens", commands)

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.ensure_stats_schema")
    def test_init_schema_handler(self, mock_ensure, _mock_ch_kwargs):
        with mock.patch("clickhouse_connect.get_client") as mock_get_client:
            messages = handlers.init_schema()

        mock_ensure.assert_called_once_with(mock_get_client.return_value)
        mock_get_client.return_value.close.assert_called_once()
        self.assertEqual(messages, [{"type": "clk_schema_initialized", "status": "success"}])

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.ensure_stats_schema", side_effect=RuntimeError("boom"))
    def test_init_schema_handler_error(self, _mock_ensure, _mock_ch_kwargs):
        with mock.patch("clickhouse_connect.get_client"):
            messages = handlers.init_schema()

        self.assertEqual(messages[0]["type"], "clk_schema_initialized")
        self.assertEqual(messages[0]["status"], "error")
        self.assertIn("boom", messages[0]["error"])


if __name__ == "__main__":
    unittest.main()
