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
        mock_send.assert_called_once_with("clickhouse.schema.init", recreate_views=False)

        mock_send.reset_mock()
        result = self.runner.invoke(request_manage.cli, ["init_schema", "--recreate-views"])
        self.assertEqual(result.exit_code, 0)
        mock_send.assert_called_once_with("clickhouse.schema.init", recreate_views=True)

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
                "artists",
                "--entity",
                "recordings",
                "--batch-size",
                "500",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        mock_send.assert_has_calls([
            mock.call("clickhouse.stats.full_refresh", entity="artists", batch_size=500),
            mock.call("clickhouse.stats.full_refresh", entity="recordings", batch_size=500),
        ])

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_cron_request_all_stats_requests_metadata_then_hourly_stats(self, mock_send):
        result = self.runner.invoke(
            request_manage.cli,
            [
                "cron_request_all_stats",
                "--stats-batch-size",
                "300",
                "--metadata-batch-size",
                "400",
                "--metadata-max-retries",
                "5",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        mock_send.assert_has_calls([
            mock.call(
                "clickhouse.metadata_cache.refresh",
                cache_types=None,
                batch_size=400,
                max_retries=5,
            ),
            mock.call("clickhouse.stats.hourly", batch_size=300),
        ])

    @mock.patch("listenbrainz.clickhouse.request_manage.send_request_to_clickhouse")
    def test_cron_request_full_stats_refresh_requests_metadata_then_full_refresh(self, mock_send):
        result = self.runner.invoke(
            request_manage.cli,
            [
                "cron_request_full_stats_refresh",
                "--stats-batch-size",
                "300",
                "--metadata-batch-size",
                "400",
                "--metadata-max-retries",
                "5",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        mock_send.assert_has_calls([
            mock.call(
                "clickhouse.metadata_cache.refresh",
                cache_types=None,
                batch_size=400,
                max_retries=5,
            ),
            mock.call("clickhouse.stats.full_refresh", batch_size=300),
        ])


if __name__ == "__main__":
    unittest.main()
