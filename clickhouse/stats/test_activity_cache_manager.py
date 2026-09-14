import unittest
from datetime import datetime, timezone

from clickhouse.stats.activity_cache_manager import (
    ActivityStatsCacheManager,
    get_daily_activity_range,
    get_listening_activity_range,
)
from clickhouse.stats.cache_manager import CacheConfig


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


class ActivityValidationTestCase(unittest.TestCase):
    def test_rejects_unknown_stat_types(self):
        with self.assertRaises(ValueError):
            ActivityStatsCacheManager(CacheConfig(), "artists")
