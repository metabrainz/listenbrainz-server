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
    def test_import_full_dump(self, mock_send):
        result = self.runner.invoke(request_manage.cli, ["import_full_dump", "--workers", "2"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.import_full_dump", workers=2)

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
    def test_set_dump_import_state(self, mock_send):
        result = self.runner.invoke(request_manage.cli, ["set_dump_import_state", "--dump-id", "2560"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.set_dump_import_state", dump_id=2560)

        result = self.runner.invoke(request_manage.cli, ["set_dump_import_state"])
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
