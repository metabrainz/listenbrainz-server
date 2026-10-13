import unittest

from clickhouse.stats.activity_cache_manager import (
    DAILY_ACTIVITY,
    LISTENING_ACTIVITY,
    ActivityStatsCacheManager,
)
from clickhouse.client import ClickHouseConnection


class StatsCacheManagerMessageTestCase(unittest.TestCase):

    def test_generate_stats_messages_uses_listenbrainz_stats_contract(self):
        manager = ActivityStatsCacheManager(ClickHouseConnection(), DAILY_ACTIVITY)

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

    def test_generate_stats_messages_batches_users(self):
        manager = ActivityStatsCacheManager(ClickHouseConnection(), LISTENING_ACTIVITY)
        stats = [{"time_range": "x", "listen_count": 1}]

        messages = list(manager.generate_stats_messages(
            "all_time",
            {uid: stats for uid in range(5)},
            from_ts=1,
            to_ts=2,
            database="listening_activity_all_time_20260101",
            batch_size=2,
        ))

        self.assertEqual([[u["user_id"] for u in m["data"]] for m in messages], [[0, 1], [2, 3], [4]])
        for message in messages:
            self.assertEqual(message["database"], "listening_activity_all_time_20260101")
