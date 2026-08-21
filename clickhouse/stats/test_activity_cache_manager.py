import unittest
from contextlib import contextmanager
from datetime import date, datetime, timezone

from clickhouse.stats.activity_cache_manager import (
    DAILY_ACTIVITY_CONFIG,
    LISTENING_ACTIVITY_CONFIG,
    ActivityStatsCacheManager,
    BulkActivityStatsCacheManager,
    get_daily_activity_range,
    get_listening_activity_range,
)
from clickhouse.stats.cache_manager import CacheConfig, TIME_RANGES


class ActivityRangeTestCase(unittest.TestCase):

    def test_daily_ranges_match_spark_boundaries(self):
        latest = datetime(2021, 11, 24, 2, 3, tzinfo=timezone.utc)

        this_week = get_daily_activity_range("this_week", latest)
        previous_week = get_daily_activity_range("week", latest)

        self.assertEqual(this_week.start, datetime(2021, 11, 22, tzinfo=timezone.utc))
        self.assertEqual(this_week.end, datetime(2021, 11, 29, tzinfo=timezone.utc))
        self.assertTrue(this_week.end_inclusive)
        self.assertEqual(previous_week.start, datetime(2021, 11, 15, tzinfo=timezone.utc))
        self.assertEqual(previous_week.end, datetime(2021, 11, 22, tzinfo=timezone.utc))

    def test_daily_ranges_handle_period_first_day_like_spark(self):
        latest = datetime(2021, 11, 1, 3, tzinfo=timezone.utc)
        this_month = get_daily_activity_range("this_month", latest)

        self.assertEqual(this_month.start, datetime(2021, 10, 1, tzinfo=timezone.utc))
        self.assertEqual(this_month.end, datetime(2021, 11, 1, tzinfo=timezone.utc))

    def test_listening_week_has_two_complete_week_buckets(self):
        latest = datetime(2021, 8, 9, 2, 3, tzinfo=timezone.utc)
        activity_range = get_listening_activity_range("week", latest)

        self.assertEqual(activity_range.start, datetime(2021, 7, 26, tzinfo=timezone.utc))
        self.assertEqual(activity_range.end, datetime(2021, 8, 9, tzinfo=timezone.utc))
        self.assertEqual(len(activity_range.buckets), 14)
        self.assertEqual(activity_range.buckets[0].time_range, "Monday 26 July 2021")
        self.assertEqual(activity_range.buckets[-1].time_range, "Sunday 08 August 2021")
        self.assertEqual(
            activity_range.buckets[0].to_ts,
            int(datetime(2021, 7, 27, tzinfo=timezone.utc).timestamp()) - 1,
        )

    def test_listening_ranges_match_spark_quarter_and_half_year_bounds(self):
        quarter = get_listening_activity_range(
            "quarter", datetime(2021, 8, 9, 2, 3, tzinfo=timezone.utc),
        )
        half_year = get_listening_activity_range(
            "half_yearly", datetime(2021, 9, 7, 2, 3, tzinfo=timezone.utc),
        )

        self.assertEqual(quarter.start, datetime(2021, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(quarter.end, datetime(2021, 7, 1, tzinfo=timezone.utc))
        self.assertEqual(half_year.start, datetime(2020, 7, 1, tzinfo=timezone.utc))
        self.assertEqual(half_year.end, datetime(2021, 7, 1, tzinfo=timezone.utc))

    def test_all_time_buckets_start_at_lastfm_founding_year(self):
        latest = datetime(2021, 8, 9, 2, 3, tzinfo=timezone.utc)
        activity_range = get_listening_activity_range("all_time", latest)

        self.assertEqual(activity_range.from_ts, int(datetime(2002, 1, 1, tzinfo=timezone.utc).timestamp()))
        self.assertEqual(activity_range.to_ts, int(latest.timestamp()))
        self.assertEqual(activity_range.buckets[0].time_range, "2002")
        self.assertEqual(activity_range.buckets[-1].time_range, "2021")


class CapturingClient:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.queries = []
        self.commands = []
        self.stream_rows = []

    def query(self, sql, parameters=None):
        self.queries.append((sql, parameters or {}))

        class Result:
            def __init__(self, rows):
                self.result_rows = rows
                self.first_row = rows[0] if rows else None

        return Result(self.rows)

    def command(self, sql, parameters=None):
        self.commands.append(sql)

    @contextmanager
    def query_row_block_stream(self, sql, parameters=None):
        self.queries.append((sql, parameters or {}))
        yield iter([self.stream_rows])


class ActivityQueryTestCase(unittest.TestCase):

    def test_daily_activity_uses_utc_weekday_and_hour(self):
        manager = ActivityStatsCacheManager(CacheConfig(), DAILY_ACTIVITY_CONFIG)
        manager._latest_listen = datetime(2021, 8, 9, 2, 3, tzinfo=timezone.utc)
        manager.ch_client = CapturingClient(rows=[(42, 1, 8, 3), (42, 7, 21, 2)])

        result = manager.compute_activity_batch("all_time", [42])

        sql, parameters = manager.ch_client.queries[0]
        self.assertIn("toDayOfWeek(toTimeZone(listened_at, 'UTC'))", sql)
        self.assertIn("toHour(toTimeZone(listened_at, 'UTC'))", sql)
        self.assertEqual(parameters["user_ids"], [42])
        self.assertEqual(result[42], [
            {"day": "Monday", "hour": 8, "listen_count": 3},
            {"day": "Sunday", "hour": 21, "listen_count": 2},
        ])

    def test_listening_activity_fills_zero_count_buckets(self):
        manager = ActivityStatsCacheManager(CacheConfig(), LISTENING_ACTIVITY_CONFIG)
        manager._latest_listen = datetime(2021, 1, 2, 2, 3, tzinfo=timezone.utc)
        manager.ch_client = CapturingClient(rows=[(42, 2021, 7)])

        result = manager.compute_activity_batch("all_time", [42])

        self.assertEqual(result[42][0]["time_range"], "2002")
        self.assertEqual(result[42][0]["listen_count"], 0)
        self.assertEqual(result[42][-1]["time_range"], "2021")
        self.assertEqual(result[42][-1]["listen_count"], 7)
        sql, _ = manager.ch_client.queries[0]
        self.assertIn("FROM user_recording_stats_daily", sql)
        self.assertIn("toYear(date) AS bucket_key", sql)

    def test_stale_users_are_scoped_to_activity_bounds(self):
        manager = ActivityStatsCacheManager(CacheConfig(), DAILY_ACTIVITY_CONFIG)
        manager._latest_listen = datetime(2021, 11, 24, 2, 3, tzinfo=timezone.utc)
        manager.ch_client = CapturingClient(rows=[(1,), (2,)])

        users = manager.get_stale_users("week", date(2021, 11, 15), date(2021, 11, 22))

        self.assertEqual(users, [1, 2])
        sql, parameters = manager.ch_client.queries[0]
        self.assertIn("l.created > c.last_computed_created", sql)
        self.assertIn("s.listened_at >=", sql)
        self.assertEqual(parameters["from_ms"], 1636934400000)
        self.assertEqual(parameters["to_ms"], 1637539200000)


class BulkActivityQueryTestCase(unittest.TestCase):

    def test_daily_intermediate_has_one_conditional_count_per_range(self):
        manager = BulkActivityStatsCacheManager(CacheConfig(), DAILY_ACTIVITY_CONFIG)
        manager._latest_listen = datetime(2026, 8, 21, 12, tzinfo=timezone.utc)
        manager.ch_client = CapturingClient()

        manager.build_intermediate_table()

        sql = manager.ch_client.commands[0]
        self.assertIn("FROM listens", sql)
        self.assertIn("GROUP BY user_id, day_of_week, hour", sql)
        for time_range in TIME_RANGES:
            self.assertIn(f"AS count_{time_range}", sql)

    def test_listening_intermediate_uses_existing_daily_aggregate(self):
        manager = BulkActivityStatsCacheManager(CacheConfig(), LISTENING_ACTIVITY_CONFIG)
        manager._latest_listen = datetime(2026, 8, 21, 12, tzinfo=timezone.utc)
        manager.ch_client = CapturingClient()

        manager.build_intermediate_table()

        sql = manager.ch_client.commands[0]
        self.assertIn("FROM user_recording_stats_daily", sql)
        self.assertIn("GROUP BY user_id, date", sql)
        self.assertNotIn("FROM listens", sql)

    def test_bulk_listening_stream_emits_spark_shaped_rows(self):
        manager = BulkActivityStatsCacheManager(CacheConfig(), LISTENING_ACTIVITY_CONFIG)
        manager._latest_listen = datetime(2021, 1, 2, 2, 3, tzinfo=timezone.utc)
        client = CapturingClient()
        client.stream_rows = [(42, [(2021, 7)])]
        manager.ch_client = client

        rows = list(manager.stream_activity_for_range("all_time"))

        self.assertEqual(rows[0][0], 42)
        self.assertEqual(rows[0][1][-1]["time_range"], "2021")
        self.assertEqual(rows[0][1][-1]["listen_count"], 7)


if __name__ == "__main__":
    unittest.main()
