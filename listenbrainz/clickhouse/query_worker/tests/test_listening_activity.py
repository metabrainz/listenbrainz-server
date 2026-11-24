from datetime import datetime, timezone

from freezegun import freeze_time

from listenbrainz.clickhouse.query_worker.tests import ActivityTestCase
from listenbrainz.db import couchdb


class ListeningActivityTestCase(ActivityTestCase):
    query_name = "clickhouse.listening_activity"

    @freeze_time("2024-03-01 12:00:00")
    def test_calendar_comparisons(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at) VALUES
              (1, '2023-12-31 23:59:59'), (1, '2024-01-01 00:00:00'),
              (1, '2024-02-12 00:00:00'), (2, '2024-02-26 00:00:00'),
              (1, '2024-02-29 00:00:00'), (1, '2024-02-29 23:59:59'),
              (1, '2024-03-01 09:00:00'), (3, '2024-03-02 00:00:00')
        """)
        messages = self.refresh(None)
        expected = {
            # First and last bucket, number of buckets, total listens.
            "week": ("Monday 12 February 2024", "Sunday 25 February 2024", 14, 1),
            "this_week": ("Monday 19 February 2024", "Thursday 29 February 2024", 11, 2),
            "month": ("01 January 2024", "29 February 2024", 60, 4),
            "this_month": ("01 January 2024", "29 February 2024", 60, 4),
            "quarter": ("01 July 2023", "31 December 2023", 184, 1),
            "half_yearly": ("January 2023", "December 2023", 12, 1),
            "year": ("January 2022", "December 2023", 24, 1),
            "this_year": ("January 2023", "February 2024", 14, 5),
            "all_time": ("2002", "2024", 23, 6),
        }
        for stats_range, (first, last, length, total) in expected.items():
            with self.subTest(stats_range=stats_range):
                database, = couchdb.list_databases(f"clickhouse_listening_activity_{stats_range}_")
                # User 2 listened exactly at the completed week's exclusive end.
                includes_user_2 = stats_range in ("this_week", "month", "this_month", "this_year", "all_time")
                self.assertEqual(couchdb.get_document_count(database), 2 if includes_user_2 else 1)
                doc = couchdb.fetch_exact_data(database, "1")
                buckets = doc["data"]
                self.assertEqual(len(buckets), length)
                self.assertEqual((buckets[0]["time_range"], buckets[-1]["time_range"]), (first, last))
                self.assertEqual(sum(b["listen_count"] for b in buckets), total)
                self.assertEqual(buckets[0]["from_ts"], doc["from_ts"])
                for before, after in zip(buckets, buckets[1:]):
                    self.assertEqual(before["to_ts"] + 1, after["from_ts"])
                if stats_range == "week":
                    self.assertEqual([b["listen_count"] for b in buckets], [1] + [0] * 13)
                    self.assertEqual(doc["to_ts"], int(datetime(2024, 2, 26, tzinfo=timezone.utc).timestamp()))
                if stats_range == "this_month":
                    leap_day = int(datetime(2024, 2, 29, tzinfo=timezone.utc).timestamp())
                    self.assertEqual(buckets[-1], {"time_range": last, "from_ts": leap_day,
                                                   "to_ts": leap_day + 86399, "listen_count": 2})
                    self.assertEqual(buckets[-2]["listen_count"], 0)
                    self.assertEqual(doc["to_ts"], leap_day + 86400)
        self.assertEqual(len([m for m in messages if m["type"] == "clk_listening_activity_end"]), len(expected))
