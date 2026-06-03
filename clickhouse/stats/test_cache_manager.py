import unittest

from clickhouse.stats.cache_manager import (
    ARTIST_CONFIG,
    CacheConfig,
    RECORDING_CONFIG,
    RELEASE_GROUP_CONFIG,
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
            database_prefix="clk_recordings_all_time",
        ))

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "clk_user_entity")
        self.assertEqual(messages[0]["entity"], "recordings")
        self.assertEqual(messages[0]["stats_range"], "all_time")
        self.assertEqual(messages[0]["from_ts"], 1)
        self.assertEqual(messages[0]["to_ts"], 2)
        self.assertEqual(messages[0]["database_prefix"], "clk_recordings_all_time")
        self.assertNotIn("database", messages[0])
        self.assertEqual(messages[0]["data"][0]["user_id"], 42)
        self.assertEqual(messages[0]["data"][0]["count"], 1)
        self.assertEqual(messages[0]["data"][0]["data"][0]["listen_count"], 3)

    def test_database_names_use_api_entity_prefixes(self):
        manager = StatsCacheManager(CacheConfig(), RECORDING_CONFIG)

        self.assertEqual(
            manager.get_stats_database_prefix("recordings", "all_time"),
            "clk_recordings_all_time",
        )
        self.assertRegex(
            manager.get_stats_database_name("recordings", "all_time", with_timestamp=True),
            r"^clk_recordings_all_time_\d{8}$",
        )

    def test_database_lifecycle_messages_are_clickhouse_stats_messages(self):
        manager = StatsCacheManager(CacheConfig(), RECORDING_CONFIG)

        self.assertEqual(
            manager.generate_start_message("all_time", "clk_recordings_all_time_20260523")["type"],
            "clk_stats_database_start",
        )
        self.assertEqual(
            manager.generate_end_message("all_time", "clk_recordings_all_time_20260523")["type"],
            "clk_stats_database_end",
        )

    def test_full_refresh_does_not_create_databases_when_no_users_exist(self):
        class EmptyResultClient:
            def query(self, query):
                return type("Result", (), {"result_rows": []})()

        manager = StatsCacheManager(CacheConfig(), RECORDING_CONFIG)
        manager.ch_client = EmptyResultClient()

        self.assertEqual(list(manager.run_full_refresh()), [])

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


class StatsCacheManagerQueryTestCase(unittest.TestCase):

    class _CapturingClient:
        def __init__(self):
            self.queries = []

        def query(self, query, parameters=None):
            self.queries.append((query, parameters))
            return type("Result", (), {"result_rows": []})()

    def _run_query(self, entity_config):
        manager = StatsCacheManager(CacheConfig(), entity_config)
        manager.ch_client = self._CapturingClient()
        manager.compute_top_entities_batch("all_time", [1, 2, 3], limit=10)
        self.assertEqual(len(manager.ch_client.queries), 1)
        return manager.ch_client.queries[0][0]

    def test_top_entities_query_does_not_use_final(self):
        for cfg in (RECORDING_CONFIG, ARTIST_CONFIG):
            with self.subTest(entity=cfg.entity_type):
                sql = self._run_query(cfg)
                self.assertNotIn(" FINAL ", sql)
                self.assertNotIn(f"{cfg.dimension_table} d FINAL", sql)

    def test_top_entities_query_dedupes_metadata_via_limit_1_by(self):
        sql = self._run_query(RECORDING_CONFIG)
        self.assertIn("dedup_metadata AS", sql)
        self.assertIn("ORDER BY recording_id, updated_at DESC", sql)
        self.assertIn("LIMIT 1 BY recording_id", sql)
        self.assertIn("LEFT JOIN dedup_metadata d ON t.recording_id = d.recording_id", sql)

    def test_top_entities_query_prefilters_metadata_by_top_n_ids(self):
        sql = self._run_query(ARTIST_CONFIG)
        self.assertIn(
            "WHERE artist_id IN (SELECT artist_id FROM top_n)",
            sql,
        )

    def test_top_entities_query_filters_entities_failing_lb_validation(self):
        # Artist/recording records require artist_name >= 1 on the LB side; drop empty.
        for cfg in (ARTIST_CONFIG, RECORDING_CONFIG):
            with self.subTest(entity=cfg.entity_type):
                sql = self._run_query(cfg)
                self.assertIn("d.artist_name != ''", sql)

    def test_top_entities_query_does_not_filter_when_no_predicate(self):
        # Release groups have no min_length on artist_name; no filter applied.
        self.assertIsNone(RELEASE_GROUP_CONFIG.valid_entity_predicate)
        sql = self._run_query(RELEASE_GROUP_CONFIG)
        self.assertNotIn("d.artist_name != ''", sql)


if __name__ == "__main__":
    unittest.main()
