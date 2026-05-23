import unittest

from clickhouse.stats.cache_manager import (
    CacheConfig,
    RECORDING_CONFIG,
    StatsCacheManager,
    _format_entity_tuple,
)


class StatsCacheManagerMessageTestCase(unittest.TestCase):

    def test_generate_stats_messages_uses_listenbrainz_stats_contract(self):
        manager = StatsCacheManager(CacheConfig(), RECORDING_CONFIG)

        messages = list(manager.generate_stats_messages(
            "all_time",
            {
                42: [{
                    "recording_mbid": "4f2e0853-1c4f-4d39-94a6-7e5ad08f63d0",
                    "track_name": "A Song",
                    "artist_name": "An Artist",
                    "artist_mbids": [],
                    "release_name": "",
                    "release_mbid": None,
                    "artists": [],
                    "caa_id": 0,
                    "caa_release_mbid": None,
                    "listen_count": 3,
                }],
            },
            from_ts=1,
            to_ts=2,
            database_prefix="recordings_all_time",
        ))

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "clk_user_entity")
        self.assertEqual(messages[0]["entity"], "recordings")
        self.assertEqual(messages[0]["stats_range"], "all_time")
        self.assertEqual(messages[0]["from_ts"], 1)
        self.assertEqual(messages[0]["to_ts"], 2)
        self.assertEqual(messages[0]["database_prefix"], "recordings_all_time")
        self.assertNotIn("database", messages[0])
        self.assertEqual(messages[0]["data"][0]["user_id"], 42)
        self.assertEqual(messages[0]["data"][0]["count"], 1)
        self.assertEqual(messages[0]["data"][0]["data"][0]["listen_count"], 3)

    def test_database_names_use_api_entity_prefixes(self):
        manager = StatsCacheManager(CacheConfig(), RECORDING_CONFIG)

        self.assertEqual(
            manager.get_stats_database_prefix("recordings", "all_time"),
            "recordings_all_time",
        )
        self.assertRegex(
            manager.get_stats_database_name("recordings", "all_time", with_timestamp=True),
            r"^recordings_all_time_\d{8}$",
        )

    def test_database_lifecycle_messages_are_clickhouse_stats_messages(self):
        manager = StatsCacheManager(CacheConfig(), RECORDING_CONFIG)

        self.assertEqual(
            manager.generate_start_message("all_time", "recordings_all_time_20260523")["type"],
            "clk_stats_database_start",
        )
        self.assertEqual(
            manager.generate_end_message("all_time", "recordings_all_time_20260523")["type"],
            "clk_stats_database_end",
        )

    def test_dimension_fields_transform_clickhouse_metadata_shape(self):
        entity = _format_entity_tuple(
            (
                "4f2e0853-1c4f-4d39-94a6-7e5ad08f63d0",
                "A Song",
                "An Artist",
                ["", "f59c5520-5f46-4d2c-b2c4-822eabf53419"],
                "",
                None,
                (
                    '[{"artist_credit_name": "An Artist", "join_phrase": "", '
                    '"artist_mbid": "f59c5520-5f46-4d2c-b2c4-822eabf53419"}]'
                ),
                0,
                "",
                3,
            ),
            RECORDING_CONFIG.dimension_fields,
        )

        self.assertEqual(entity["artist_mbids"], ["f59c5520-5f46-4d2c-b2c4-822eabf53419"])
        self.assertEqual(entity["artists"][0]["artist_credit_name"], "An Artist")
        self.assertEqual(entity["listen_count"], 3)


if __name__ == "__main__":
    unittest.main()
