import unittest

from clickhouse.stats.activity_cache_manager import (
    DAILY_ACTIVITY,
    LISTENING_ACTIVITY,
    ActivityStatsCacheManager,
)
from clickhouse.stats.cache_manager import CacheConfig, StatsCacheManager


class StatsCacheManagerMessageTestCase(unittest.TestCase):

    def test_generate_stats_messages_uses_listenbrainz_stats_contract(self):
        manager = ActivityStatsCacheManager(CacheConfig(), DAILY_ACTIVITY)

        messages = list(manager.generate_stats_messages(
            "all_time",
            {
                42: [{"day": "Monday", "hour": 8, "listen_count": 3}],
            },
            from_ts=1,
            to_ts=2,
            database_prefix="daily_activity_all_time",
        ))

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "clk_user_entity")
        self.assertEqual(messages[0]["entity"], "daily_activity")
        self.assertEqual(messages[0]["stats_range"], "all_time")
        self.assertEqual(messages[0]["from_ts"], 1)
        self.assertEqual(messages[0]["to_ts"], 2)
        self.assertEqual(messages[0]["database_prefix"], "daily_activity_all_time")
        self.assertNotIn("database", messages[0])
        self.assertEqual(messages[0]["data"][0]["user_id"], 42)
        self.assertEqual(messages[0]["data"][0]["count"], 1)
        self.assertEqual(messages[0]["data"][0]["data"][0]["listen_count"], 3)

    def test_generate_stats_messages_splits_batches_by_payload_size(self):
        manager = ActivityStatsCacheManager(CacheConfig(), LISTENING_ACTIVITY)
        # ~1 KiB of stats per user; with a 2.5 KiB cap, at most two users fit per message.
        stats = [{"time_range": "x" * 1000, "listen_count": 1}]
        user_results = {uid: stats for uid in range(5)}

        messages = list(manager.generate_stats_messages(
            "all_time",
            user_results,
            from_ts=1,
            to_ts=2,
            database="listening_activity_all_time_20260101",
            batch_size=100,
            max_message_bytes=2500,
        ))

        self.assertEqual([len(m["data"]) for m in messages], [2, 2, 1])
        self.assertEqual(
            [u["user_id"] for m in messages for u in m["data"]],
            [0, 1, 2, 3, 4],
        )
        for message in messages:
            self.assertEqual(message["database"], "listening_activity_all_time_20260101")

    def test_generate_stats_messages_sends_oversized_single_user_alone(self):
        manager = ActivityStatsCacheManager(CacheConfig(), LISTENING_ACTIVITY)
        big = [{"time_range": "x" * 5000, "listen_count": 1}]
        small = [{"time_range": "y", "listen_count": 1}]

        messages = list(manager.generate_stats_messages(
            "all_time",
            {1: small, 2: big, 3: small},
            from_ts=1,
            to_ts=2,
            max_message_bytes=1000,
        ))

        self.assertEqual([[u["user_id"] for u in m["data"]] for m in messages], [[1], [2], [3]])

    def test_database_names_use_api_stat_prefixes(self):
        manager = ActivityStatsCacheManager(CacheConfig(), LISTENING_ACTIVITY)

        self.assertEqual(
            manager.get_stats_database_prefix("listening_activity", "all_time"),
            "listening_activity_all_time",
        )
        self.assertRegex(
            manager.get_stats_database_name("listening_activity", "all_time", with_timestamp=True),
            r"^listening_activity_all_time_\d{8}$",
        )

    def test_database_names_carry_the_configured_prefix(self):
        manager = ActivityStatsCacheManager(CacheConfig(couch_db_prefix="clk"), DAILY_ACTIVITY)

        self.assertEqual(
            manager.get_stats_database_prefix("daily_activity", "week"),
            "clk_daily_activity_week",
        )

    def test_database_lifecycle_messages_are_clickhouse_stats_messages(self):
        manager = ActivityStatsCacheManager(CacheConfig(), DAILY_ACTIVITY)

        start = manager.generate_start_message("all_time", "daily_activity_all_time_20260523")
        end = manager.generate_end_message("all_time", "daily_activity_all_time_20260523")

        self.assertEqual(start["type"], "clk_stats_database_start")
        self.assertEqual(start["entity_type"], "daily_activity")
        self.assertEqual(end["type"], "clk_stats_database_end")
        self.assertEqual(end["entity_type"], "daily_activity")


class StatsCacheManagerBaseTestCase(unittest.TestCase):

    def test_base_manager_leaves_stat_specific_queries_to_subclasses(self):
        manager = StatsCacheManager(CacheConfig(), "daily_activity")

        with self.assertRaises(NotImplementedError):
            manager.get_stale_users("all_time", None, None)
        with self.assertRaises(NotImplementedError):
            manager.get_period_bounds("all_time")


if __name__ == "__main__":
    unittest.main()
