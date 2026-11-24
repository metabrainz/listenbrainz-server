from unittest.mock import patch

from freezegun import freeze_time

from listenbrainz.clickhouse.query_worker.listens.aggregates import LIVE_STREAM
from listenbrainz.clickhouse.query_worker.listens.deletions import delete_matching_listens
from listenbrainz.clickhouse.query_worker.query_map import functions
from listenbrainz.clickhouse.query_worker.tests import ActivityTestCase
from listenbrainz.clickhouse.result_consumer.handlers import get_handler
from listenbrainz.db import couchdb


class DailyActivityTestCase(ActivityTestCase):
    query_name = "clickhouse.daily_activity"

    def test_rollup_batches_and_replacement(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at)
            SELECT number + 1, toDateTime('2024-01-01 09:00:00', 'UTC') FROM numbers(26)
        """)
        self.client.command("""
            INSERT INTO listens (user_id, listened_at) VALUES
              (1, '2024-01-01 09:30:00'), (1, '2024-01-08 09:45:00'), (2, '2024-02-01 00:00:00'),
              (2, '2024-02-01 00:00:00.001'), (3, '2024-02-01 04:00:00')
        """)
        with freeze_time("2024-02-12 10:00:00"):
            messages = self.refresh(["all_time", "month"])
        for stats_range in ("all_time", "month"):
            batches = [m for m in messages if m.get("stats_range") == stats_range]
            self.assertEqual([len(m["data"]) for m in batches], [25, 1])
            database = batches[0]["database"]
            doc = couchdb.fetch_exact_data(database, "1")
            self.assertEqual(doc["data"], [{"day": "Monday", "hour": 9, "listen_count": 3}])
            doc = couchdb.fetch_exact_data(database, "2")
            expected = [{"day": "Monday", "hour": 9, "listen_count": 1}]
            if stats_range == "all_time":
                expected.append({"day": "Thursday", "hour": 0, "listen_count": 2})
            self.assertEqual(doc["data"], expected)
            self.assertEqual(doc["to_ts"], 1707782399 if stats_range == "all_time" else 1706745600)
            doc = couchdb.fetch_exact_data(database, "3")
            self.assertEqual(len(doc["data"]), 2 if stats_range == "all_time" else 1)

        # A new snapshot must discard old users, even when the range becomes empty.
        delete_matching_listens(self.client, "listens", "1", LIVE_STREAM)
        with freeze_time("2024-02-12 11:00:00"):
            empty = self.refresh(["month"])
        self.assertEqual(empty[-1]["user_count"], 0)
        self.assertEqual(couchdb.list_databases("clickhouse_daily_activity_month_"), [empty[-1]["database"]])

    def test_missing_batch_preserves_previous_database(self):
        self.client.command("INSERT INTO listens (user_id, listened_at) VALUES (1, '2024-01-01 00:00:00')")
        complete = self.refresh(["all_time"])[-1]["database"]
        with patch.object(type(self.connection), "from_config", return_value=self.connection):
            start, batch, end = functions["clickhouse.daily_activity"](["all_time"])
        get_handler(start["type"])(start)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            get_handler(end["type"])(end)
        self.assertIsNotNone(couchdb.fetch_exact_data(complete, "1"))

        # A replayed batch replaces its document and still counts as one user.
        for _ in range(2):
            get_handler(batch["type"])(batch)
        get_handler(end["type"])(end)
        self.assertEqual(couchdb.list_databases("clickhouse_daily_activity_all_time_"), [end["database"]])

    @freeze_time("2024-01-15 12:00:00")
    def test_overlapping_refreshes_keep_their_snapshot(self):
        self.client.command("INSERT INTO listens (user_id, listened_at) VALUES (1, '2024-01-02 09:00:00')")
        with patch.object(type(self.connection), "from_config", return_value=self.connection):
            original = functions["clickhouse.daily_activity"](["this_month", "all_time"])
            self.addCleanup(original.close)
            next(original)  # The job has pinned its counts and captured its UTC reference date.
            self.client.command("INSERT INTO listens (user_id, listened_at) VALUES (2, '2024-01-03 10:00:00')")
            newer = list(functions["clickhouse.daily_activity"](["all_time"]))
            older = list(original)

        self.assertEqual(newer[-1]["user_count"], 2)
        batches = [m for m in older if m["type"] == "clk_daily_activity"]
        self.assertEqual(len(batches), 2)
        for batch in batches:
            self.assertEqual([entry["user_id"] for entry in batch["data"]], [1])
        self.assertEqual(batches[-1]["to_ts"], 1705363199)

    @freeze_time("2024-01-01 12:00:00")
    def test_current_ranges_start_on_calendar_boundary(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at) VALUES
              (1, '2023-12-31 23:59:59'), (2, '2024-01-01 00:00:00'), (3, '2024-01-02 00:00:00')
        """)
        messages = self.refresh(["this_week", "this_month", "this_year", "all_time"])
        batches = [m for m in messages if m["type"] == "clk_daily_activity"]
        self.assertEqual(len(batches), 4)
        for batch in batches:
            users = {row["user_id"] for row in batch["data"]}
            if batch["stats_range"] == "all_time":
                self.assertEqual(users, {1, 2})
            else:
                self.assertEqual(batch["from_ts"], 1704067200)
                self.assertEqual(users, {2})
