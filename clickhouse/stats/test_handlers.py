import unittest
from unittest import mock

from clickhouse.stats import handlers


class DumpHandlerTestCase(unittest.TestCase):

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.load_from_ftp")
    def test_import_incremental_dump_reports_load_errors(self, mock_load_from_ftp, _mock_ch_kwargs):
        mock_load_from_ftp.return_value = {
            "dump_id": 2534,
            "total_inserted": 0,
            "files_completed": 0,
            "errors": [("/tmp/0.parquet", "HTTP request URI invalid or too long")],
        }

        messages = handlers.import_incremental_dump()

        self.assertEqual(messages[0]["type"], "clk_dump_imported")
        self.assertEqual(messages[0]["status"], "error")
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
    @mock.patch("clickhouse.stats.handlers.load_from_ftp")
    def test_import_incremental_dump_never_replaces(self, mock_load_from_ftp, _mock_ch_kwargs):
        mock_load_from_ftp.return_value = {
            "dump_id": 1, "load_id": "abc", "total_inserted": 10, "files_completed": 1, "errors": [],
        }
        messages = handlers.import_incremental_dump()
        self.assertEqual(mock_load_from_ftp.call_args.kwargs["replace"], False)
        self.assertFalse(messages[0]["replace"])


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


class SchemaHandlerTestCase(unittest.TestCase):

    def test_ensure_stats_schema_does_not_drop_views_by_default(self):
        from clickhouse.stats import schema

        client = mock.Mock()
        client.query.return_value.result_rows = [("load_id",)]
        schema.ensure_stats_schema(client)
        commands = [c.args[0] for c in client.command.call_args_list]
        self.assertFalse(any("DROP TABLE" in c for c in commands))
        self.assertTrue(all("IF NOT EXISTS" in c or "CREATE OR REPLACE FUNCTION" in c for c in commands))
        self.assertEqual(
            len([c for c in commands if "CREATE MATERIALIZED VIEW" in c]),
            len(schema.MATERIALIZED_VIEW_NAMES),
        )

    def test_ensure_stats_schema_recreates_views_on_request(self):
        from clickhouse.stats import schema

        client = mock.Mock()
        client.query.return_value.result_rows = [("load_id",)]
        schema.ensure_stats_schema(client, recreate_views=True)
        commands = [c.args[0] for c in client.command.call_args_list]
        drops = [c for c in commands if c.startswith("DROP TABLE IF EXISTS")]
        self.assertEqual(len(drops), len(schema.MATERIALIZED_VIEW_NAMES))
        for view_name in schema.MATERIALIZED_VIEW_NAMES:
            self.assertIn(f"DROP TABLE IF EXISTS {view_name}", commands)
            self.assertLess(
                commands.index(f"DROP TABLE IF EXISTS {view_name}"),
                next(i for i, c in enumerate(commands) if f"IF NOT EXISTS {view_name}" in c),
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
        self.assertIn("DROP TABLE IF EXISTS mv_raw_listens_to_submitted_artist_metadata", commands)
        self.assertLess(
            commands.index("DROP TABLE raw_listens"),
            next(i for i, c in enumerate(commands) if "IF NOT EXISTS mv_raw_listens_to_submitted_artist_metadata" in c),
        )
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
            messages = handlers.init_schema(recreate_views=True)

        mock_ensure.assert_called_once_with(mock_get_client.return_value, recreate_views=True)
        mock_get_client.return_value.close.assert_called_once()
        self.assertEqual(messages, [{"type": "clk_schema_initialized", "status": "success", "recreate_views": True}])

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
