import unittest
from contextlib import contextmanager
from datetime import date, datetime, timezone

from clickhouse.stats.bulk_cache_manager import (
    BulkStatsCacheManager,
    _to_sumif_predicate,
)
from clickhouse.stats.cache_manager import (
    ARTIST_CONFIG,
    CacheConfig,
    RECORDING_CONFIG,
    TIME_RANGES,
)


class FakeStream:
    def __init__(self, blocks):
        self._blocks = blocks

    def __enter__(self):
        return iter(self._blocks)

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeClient:
    """Records commands and lets tests script query/stream responses by SQL substring."""

    def __init__(self):
        self.commands = []
        self.queries = []
        self.stream_calls = []
        self.row_count = 0
        self.max_created = None
        self.period_bounds = (date(2026, 1, 1), date(2026, 12, 31))
        self.stream_blocks_by_marker: dict[str, list[list[tuple]]] = {}

    def command(self, sql, settings=None, parameters=None):
        self.commands.append(sql)

    def query(self, sql, parameters=None):
        self.queries.append(sql)

        class _Result:
            def __init__(self, rows):
                self.result_rows = rows
                self.first_row = rows[0] if rows else None

        if "count()" in sql.lower() or "select count(" in sql.lower():
            return _Result([(self.row_count,)])
        if "max(created)" in sql:
            return _Result([(self.max_created,)])
        if "period_start_sql" in sql or "toStartOf" in sql or "toDate(" in sql:
            return _Result([self.period_bounds])
        if "user_stats_cache_state" in sql.lower():
            return _Result([])
        return _Result([])

    @contextmanager
    def query_row_block_stream(self, sql, parameters=None):
        self.stream_calls.append(sql)
        marker = next(
            (m for m in self.stream_blocks_by_marker if m in sql),
            None,
        )
        blocks = self.stream_blocks_by_marker.get(marker, [])
        yield iter(blocks)

    def insert(self, table, rows, column_names=None):
        self.commands.append(("INSERT", table, len(rows)))


class BulkSumIfPredicateTestCase(unittest.TestCase):

    def test_all_time_filter_becomes_true_predicate(self):
        self.assertEqual(_to_sumif_predicate(""), "1")

    def test_and_prefix_is_stripped(self):
        self.assertEqual(
            _to_sumif_predicate("AND s.date >= toStartOfWeek(today())"),
            "date >= toStartOfWeek(today())",
        )

    def test_predicates_cover_all_time_ranges(self):
        for tr, config in TIME_RANGES.items():
            with self.subTest(time_range=tr):
                pred = _to_sumif_predicate(config["filter"])
                self.assertNotIn(" s.", pred)
                self.assertFalse(pred.upper().startswith("AND "))


class BulkIntermediateTableSqlTestCase(unittest.TestCase):

    def test_build_intermediate_emits_one_sumif_per_time_range(self):
        manager = BulkStatsCacheManager(CacheConfig(), RECORDING_CONFIG)
        manager.ch_client = FakeClient()

        manager.build_intermediate_table()

        self.assertEqual(len(manager.ch_client.commands), 1)
        sql = manager.ch_client.commands[0]
        for tr in TIME_RANGES:
            self.assertIn(f"AS count_{tr}", sql)
        self.assertIn("FROM user_recording_stats_daily", sql)
        self.assertIn("GROUP BY user_id, recording_id", sql)
        self.assertIn("HAVING sum(listen_count) > 0", sql)

    def test_drop_intermediate_uses_safe_drop_setting(self):
        manager = BulkStatsCacheManager(CacheConfig(), ARTIST_CONFIG)
        manager.ch_client = FakeClient()

        manager.drop_intermediate_table()

        sql = manager.ch_client.commands[0]
        self.assertIn("DROP TABLE IF EXISTS tmp_bulk_user_entity_counts_artists", sql)
        self.assertIn("max_table_size_to_drop = 0", sql)

    def test_top_n_query_reads_intermediate_not_daily_table(self):
        manager = BulkStatsCacheManager(CacheConfig(), RECORDING_CONFIG)

        sql = manager.build_top_n_query("this_week")

        self.assertIn("FROM tmp_bulk_user_entity_counts_recordings", sql)
        self.assertNotIn("FROM user_recording_stats_daily", sql)
        self.assertIn("count_this_week AS listen_count", sql)
        self.assertIn("WHERE count_this_week > 0", sql)
        self.assertIn("dedup_metadata", sql)
        self.assertNotIn(" FINAL ", sql)

    def test_top_n_query_filters_entities_failing_lb_validation(self):
        sql = BulkStatsCacheManager(CacheConfig(), RECORDING_CONFIG).build_top_n_query("all_time")
        self.assertIn("d.artist_name != ''", sql)


class BulkRunFullRefreshTestCase(unittest.TestCase):

    def test_no_users_yields_no_messages_and_cleans_up(self):
        manager = BulkStatsCacheManager(CacheConfig(), RECORDING_CONFIG)
        client = FakeClient()
        client.row_count = 0
        manager.ch_client = client

        messages = list(manager.run_bulk_full_refresh())

        self.assertEqual(messages, [])
        drop_commands = [c for c in client.commands if isinstance(c, str) and "DROP TABLE" in c]
        self.assertGreaterEqual(len(drop_commands), 2)  # pre-build + finally

    def test_emits_start_data_end_per_time_range_when_users_present(self):
        manager = BulkStatsCacheManager(CacheConfig(top_n=10), ARTIST_CONFIG)
        client = FakeClient()
        client.row_count = 2
        client.max_created = datetime(2026, 5, 27, tzinfo=timezone.utc)
        manager.ch_client = client

        # Same two users yielded for every time_range
        sample_block = [
            (
                1,
                [("mbid-a", "Artist A", 5)],
            ),
            (
                2,
                [("mbid-b", "Artist B", 3)],
            ),
        ]
        for tr in TIME_RANGES:
            marker = f"count_{tr}"
            client.stream_blocks_by_marker[marker] = [sample_block]

        messages = list(manager.run_bulk_full_refresh(message_batch_size=10))

        starts = [m for m in messages if m["type"] == "clk_stats_database_start"]
        ends = [m for m in messages if m["type"] == "clk_stats_database_end"]
        data = [m for m in messages if m["type"] == "clk_user_entity"]

        self.assertEqual(len(starts), len(TIME_RANGES))
        self.assertEqual(len(ends), len(TIME_RANGES))
        self.assertEqual(len(data), len(TIME_RANGES))

        for start_msg in starts:
            self.assertRegex(
                start_msg["database"],
                r"^clk_artists_[a-z_]+_\d{8}$",
            )
        for data_msg in data:
            self.assertEqual(data_msg["entity"], "artists")
            self.assertIn(data_msg["stats_range"], TIME_RANGES)
            self.assertEqual(len(data_msg["data"]), 2)

    def test_intermediate_table_dropped_even_when_streaming_raises(self):
        manager = BulkStatsCacheManager(CacheConfig(), RECORDING_CONFIG)
        client = FakeClient()
        client.row_count = 5
        client.max_created = datetime(2026, 5, 27, tzinfo=timezone.utc)

        @contextmanager
        def broken_stream(sql, parameters=None):
            yield iter([])  # consume normally to set up
            raise RuntimeError("simulated stream failure")

        client.query_row_block_stream = broken_stream  # type: ignore[assignment]
        manager.ch_client = client

        with self.assertRaises(RuntimeError):
            list(manager.run_bulk_full_refresh())

        drop_after_build = [
            c for c in client.commands
            if isinstance(c, str) and "DROP TABLE" in c and "tmp_bulk_user_entity_counts_recordings" in c
        ]
        self.assertGreaterEqual(len(drop_after_build), 2)


if __name__ == "__main__":
    unittest.main()
