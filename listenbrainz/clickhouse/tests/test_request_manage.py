import unittest
from unittest import mock

from click.testing import CliRunner

from listenbrainz.clickhouse import request_manage


class ClickHouseRequestManageTestCase(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_init_schema(self, mock_send):
        result = self.runner.invoke(request_manage.cli, ["init_schema"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.schema.init")

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_import_full_dump_replace_flag(self, mock_send):
        result = self.runner.invoke(request_manage.cli, ["import_full_dump"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.import_full_dump", workers=4, replace=True)

        mock_send.reset_mock()
        result = self.runner.invoke(request_manage.cli, ["import_full_dump", "--no-replace", "--workers", "2"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.import_full_dump", workers=2, replace=False)

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_import_incremental_dump_max_dumps(self, mock_send):
        result = self.runner.invoke(request_manage.cli, ["import_incremental_dump"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.import_incremental_dump", workers=4, max_dumps=None)

        mock_send.reset_mock()
        result = self.runner.invoke(request_manage.cli, ["import_incremental_dump", "--max-dumps", "5"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.import_incremental_dump", workers=4, max_dumps=5)

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_record_imported_dump(self, mock_send):
        result = self.runner.invoke(request_manage.cli, [
            "record_imported_dump", "--dump-id", "2560", "--dump-type", "full",
            "--imported-at", "2026-06-10 00:21:48.531",
        ])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with(
            "clickhouse.record_imported_dump",
            dump_id=2560, dump_type="full", imported_at="2026-06-10 00:21:48.531",
        )

        mock_send.reset_mock()
        result = self.runner.invoke(request_manage.cli, [
            "record_imported_dump", "--dump-id", "2633", "--dump-type", "incremental",
        ])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with(
            "clickhouse.record_imported_dump",
            dump_id=2633, dump_type="incremental", imported_at=None,
        )

        result = self.runner.invoke(request_manage.cli, [
            "record_imported_dump", "--dump-id", "1", "--dump-type", "sample",
        ])
        self.assertNotEqual(result.exit_code, 0)

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_import_deleted_listens(self, mock_send):
        result = self.runner.invoke(request_manage.cli, ["import_deleted_listens", "--batch-size", "500"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.import_deleted_listens", batch_size=500)

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_request_hourly_stats_defaults_to_all_entities(self, mock_send):
        result = self.runner.invoke(
            request_manage.cli,
            ["request_hourly_stats", "--batch-size", "250"],
        )

        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.stats.hourly", batch_size=250)

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_request_full_stats_refresh_can_target_entities(self, mock_send):
        result = self.runner.invoke(
            request_manage.cli,
            [
                "request_full_stats_refresh",
                "--entity",
                "daily_activity",
                "--entity",
                "listening_activity",
                "--message-batch-size",
                "50",
                "--user-flush-size",
                "5000",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        mock_send.assert_has_calls([
            mock.call(
                "clickhouse.stats.full_refresh",
                entity="daily_activity",
                message_batch_size=50,
                user_flush_size=5000,
            ),
            mock.call(
                "clickhouse.stats.full_refresh",
                entity="listening_activity",
                message_batch_size=50,
                user_flush_size=5000,
            ),
        ])

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_entity_stats_cannot_be_requested(self, mock_send):
        result = self.runner.invoke(
            request_manage.cli,
            ["request_full_stats_refresh", "--entity", "artists"],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid value for '--entity'", result.output)
        mock_send.assert_not_called()

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_request_stats_can_target_activity_types(self, mock_send):
        result = self.runner.invoke(
            request_manage.cli,
            [
                "request_hourly_stats",
                "--entity",
                "daily_activity",
                "--entity",
                "listening_activity",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        mock_send.assert_has_calls([
            mock.call("clickhouse.stats.hourly", entity="daily_activity", batch_size=1000),
            mock.call("clickhouse.stats.hourly", entity="listening_activity", batch_size=1000),
        ])

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_cron_request_all_stats_requests_hourly_stats(self, mock_send):
        result = self.runner.invoke(
            request_manage.cli,
            ["cron_request_all_stats", "--stats-batch-size", "300"],
        )

        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.stats.hourly", batch_size=300)

if __name__ == "__main__":
    unittest.main()
