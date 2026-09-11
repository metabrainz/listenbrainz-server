from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from listenbrainz.db.dump_entry import add_dump_entry
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver.views import status_api


class StatusViewsTestCase(IntegrationTestCase):

    def test_dump_get_404(self):
        r = self.client.get("/1/status/get-dump-info", query_string={"id": 1})
        self.assert404(r)

    def test_dump_get_200(self):
        t0 = datetime.now(timezone.utc)
        dump_id = add_dump_entry(t0, "full")
        r = self.client.get("/1/status/get-dump-info", query_string={"id": dump_id})
        self.assert200(r)
        self.assertDictEqual(r.json, {
            "id": dump_id,
            "timestamp": t0.strftime("%Y%m%d-%H%M%S"),
            "dump_type": "full"
        })

        # should return the latest dump if no dump ID passed
        t1 = t0 + timedelta(seconds=15)
        dump_id_1 = add_dump_entry(t1, "full")
        r = self.client.get("/1/status/get-dump-info")
        self.assert200(r)
        self.assertDictEqual(r.json, {
            "id": dump_id_1,
            "timestamp": t1.strftime("%Y%m%d-%H%M%S"),
            "dump_type": "full"
        })

    def test_dump_get_400(self):
        r = self.client.get("/1/status/get-dump-info", query_string={"id": "pqrs"})
        self.assert400(r)

    def test_monitored_stats_types_match_cron_requested_statistics(self):
        self.assertEqual(
            set(status_api.get_monitored_stats_types()),
            {
                f"{stats_type}_{stats_range}"
                for stats_range in status_api.ALLOWED_STATISTICS_RANGE
                for stats_type in (
                    *status_api.MONITORED_USER_ENTITY_STATS,
                    *status_api.MONITORED_USER_NON_ENTITY_STATS,
                    *status_api.MONITORED_ENTITY_LISTENER_STATS,
                )
            }
        )

    @patch.object(status_api, "time", return_value=200)
    @patch.object(status_api, "get_global_stats_timestamp", return_value=150)
    @patch.object(status_api, "get_incoming_listens_count", return_value=0)
    @patch.object(status_api, "get_dump_timestamp", return_value=None)
    @patch.object(status_api, "get_stats_timestamps", return_value={
        "artists_week": 100,
        "recordings_week": 120,
    })
    @patch.object(status_api, "get_monitored_stats_types", return_value=[
        "artists_week",
        "recordings_week",
        "releases_week",
    ])
    def test_service_status_uses_available_stats_timestamps_when_some_are_missing(
            self,
            mock_get_monitored_stats_types,
            mock_get_stats_timestamps,
            mock_get_dump_timestamp,
            mock_get_incoming_listens_count,
            mock_get_global_stats_timestamp,
            mock_time
    ):
        with patch.object(self.app.logger, "error") as mock_logger_error:
            r = self.client.get("/1/status/service-status")

        self.assert200(r)
        self.assertEqual(r.json["stats_age"], 100)
        self.assertEqual(r.json["stats"], [
            {"name": "artists_week", "age": 100},
            {"name": "recordings_week", "age": 80},
            {"name": "releases_week", "age": None},
        ])
        mock_logger_error.assert_called_once_with(
            "No generation timestamp found for %d stats: %s",
            1,
            "releases_week"
        )

    @patch.object(status_api, "time", return_value=200)
    @patch.object(status_api, "get_global_stats_timestamp", return_value=150)
    @patch.object(status_api, "get_incoming_listens_count", return_value=0)
    @patch.object(status_api, "get_dump_timestamp", return_value=None)
    @patch.object(status_api, "get_stats_timestamps", return_value={})
    @patch.object(status_api, "get_monitored_stats_types", return_value=["artists_week"])
    def test_service_status_returns_no_stats_age_when_all_stats_timestamps_are_missing(
            self,
            mock_get_monitored_stats_types,
            mock_get_stats_timestamps,
            mock_get_dump_timestamp,
            mock_get_incoming_listens_count,
            mock_get_global_stats_timestamp,
            mock_time
    ):
        with patch.object(self.app.logger, "error") as mock_logger_error:
            r = self.client.get("/1/status/service-status")

        self.assert200(r)
        self.assertIsNone(r.json["stats_age"])
        self.assertEqual(r.json["stats"], [
            {"name": "artists_week", "age": None},
        ])
        mock_logger_error.assert_called_once_with(
            "No generation timestamp found for %d stats: %s",
            1,
            "artists_week"
        )
