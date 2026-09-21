from datetime import datetime, timedelta, timezone
from unittest.mock import call, patch

from listenbrainz.db.dump_entry import add_dump_entry
from listenbrainz.tests.integration import IntegrationTestCase


class StatusViewsTestCase(IntegrationTestCase):

    @patch('listenbrainz.webserver.views.status_api.datetime')
    @patch('listenbrainz.webserver.views.status_api._redis')
    @patch('listenbrainz.webserver.views.status_api._ts')
    def test_service_status_listen_counts(self, timescale, redis, mock_datetime):
        mock_datetime.today.return_value = datetime(2026, 1, 1, 12)
        timescale.get_total_listen_count.return_value = 1234567890
        redis.get_listen_count_for_day.side_effect = [12345, 67890]

        response = self.client.get('/1/status/service-status')
        self.assert200(response)
        self.assertEqual(response.json['listen_count'], 1234567890)
        self.assertEqual(response.json['listen_counts_per_day'], [
            {'date': '2026-01-01', 'label': 'today', 'listen_count': 12345},
            {'date': '2025-12-31', 'label': 'yesterday', 'listen_count': 67890},
        ])
        redis.get_listen_count_for_day.assert_has_calls([
            call(datetime(2026, 1, 1, 12)), call(datetime(2025, 12, 31, 12)),
        ])

        redis.get_listen_count_for_day.side_effect = [12345, 67890]
        response = self.client.post('/current-status/')
        self.assert200(response)
        self.assertEqual(response.json['listenCount'], '1,234,567,890')
        self.assertEqual(response.json['listenCountsPerDay'], [
            {'date': '2026-01-01', 'label': 'today', 'listenCount': '12,345'},
            {'date': '2025-12-31', 'label': 'yesterday', 'listenCount': '67,890'},
        ])
        self.assertEqual(timescale.get_total_listen_count.call_count, 2)

    @patch('listenbrainz.webserver.views.status_api._redis')
    @patch('listenbrainz.webserver.views.status_api._ts')
    def test_service_status_unavailable_listen_counts(self, timescale, redis):
        timescale.get_total_listen_count.side_effect = RuntimeError('Database unavailable')
        redis.get_listen_count_for_day.side_effect = [RuntimeError('Redis unavailable'), 123]

        response = self.client.get('/1/status/service-status')
        self.assert200(response)
        self.assertIsNone(response.json['listen_count'])
        self.assertIsNone(response.json['listen_counts_per_day'][0]['listen_count'])
        self.assertEqual(response.json['listen_counts_per_day'][1]['listen_count'], 123)
        self.assertIn('incoming_listen_count', response.json)

    @patch('listenbrainz.webserver.views.status_api._redis')
    @patch('listenbrainz.webserver.views.status_api._ts')
    def test_service_status_empty_listen_counts(self, timescale, redis):
        timescale.get_total_listen_count.return_value = 0
        redis.get_listen_count_for_day.side_effect = [None, 0]

        response = self.client.get('/1/status/service-status')
        self.assert200(response)
        self.assertEqual(response.json['listen_count'], 0)
        self.assertEqual([day['listen_count'] for day in response.json['listen_counts_per_day']], [0, 0])

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
