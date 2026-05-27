#!/usr/bin/env python3
"""
Bulk Stats Cache Manager

Variant of StatsCacheManager that scans user_*_stats_daily once across all
time ranges instead of once per (time_range x user_batch). It builds an
intermediate MergeTree of (user_id, entity_id, count_per_time_range) via
conditional aggregation, then streams a top-N ranking off that intermediate
once per time range. Same per-database CouchDB write contract: emits
start / data / end messages for each time_range.

Use this for full-refresh workloads where user count is high and the daily
table is large; the hourly incremental path is still served by
StatsCacheManager.run_hourly_job.
"""

import logging
import time
from typing import Iterator

from clickhouse.stats.cache_manager import (
    StatsCacheManager,
    TIME_RANGES,
    _format_entity_tuple,
)

logger = logging.getLogger(__name__)


def _to_sumif_predicate(filter_clause: str) -> str:
    """Convert a TIME_RANGES filter ('AND s.date >= ...') into a sumIf predicate.

    The aggregation here selects directly from the daily stats table (no JOIN
    alias), so the ``s.`` prefix is dropped.
    """
    pred = (filter_clause or "").strip()
    if not pred:
        return "1"
    if pred.upper().startswith("AND "):
        pred = pred[4:]
    return pred.replace("s.date", "date")


class BulkStatsCacheManager(StatsCacheManager):
    """Cache manager that uses a single intermediate scan for full refreshes."""

    INTERMEDIATE_PREFIX = "tmp_bulk_user_entity_counts_"

    @property
    def intermediate_table_name(self) -> str:
        return f"{self.INTERMEDIATE_PREFIX}{self.entity_config.entity_type}"

    def _time_range_columns(self) -> list[tuple[str, str]]:
        """Return (time_range, count_column_name) pairs in TIME_RANGES order."""
        return [(tr, f"count_{tr}") for tr in TIME_RANGES]

    def build_intermediate_table(self) -> None:
        """Materialize user x entity_id with one sumIf column per time_range.

        Scans the daily stats table exactly once. The output MergeTree is
        ORDER BY (user_id, id) so the subsequent per-time-range ranking reads
        contiguous granules.
        """
        ec = self.entity_config
        sumif_columns = ",\n                ".join(
            f"sumIf(listen_count, {_to_sumif_predicate(TIME_RANGES[tr]['filter'])}) AS {col}"
            for tr, col in self._time_range_columns()
        )
        sql = f"""
            CREATE TABLE {self.intermediate_table_name}
            ENGINE = MergeTree()
            ORDER BY (user_id, {ec.id_column})
            AS SELECT
                user_id,
                {ec.id_column},
                {sumif_columns}
            FROM {ec.stats_table}
            GROUP BY user_id, {ec.id_column}
            HAVING sum(listen_count) > 0
        """
        self.ch_client.command(sql)

    def drop_intermediate_table(self) -> None:
        self.ch_client.command(
            f"DROP TABLE IF EXISTS {self.intermediate_table_name} "
            f"SETTINGS max_table_size_to_drop = 0"
        )

    def intermediate_row_count(self) -> int:
        result = self.ch_client.query(
            f"SELECT count() FROM {self.intermediate_table_name}"
        )
        return result.first_row[0]

    def build_top_n_query(self, time_range: str) -> str:
        """Top-N ranking query over the intermediate table for one time_range."""
        ec = self.entity_config
        count_column = f"count_{time_range}"
        select_fields = self._build_select_fields()
        dimension_columns = self._build_dimension_columns()
        tuple_fields = self._build_tuple_fields()
        array_map_indices = self._build_array_map_indices()

        return f"""
            WITH ranked AS (
                SELECT
                    user_id,
                    {ec.id_column},
                    {count_column} AS listen_count,
                    row_number() OVER (
                        PARTITION BY user_id ORDER BY {count_column} DESC
                    ) AS rn
                FROM {self.intermediate_table_name}
                WHERE {count_column} > 0
            ),
            top_n AS (
                SELECT user_id, {ec.id_column}, listen_count
                FROM ranked
                WHERE rn <= {{limit:UInt32}}
            ),
            dedup_metadata AS (
                SELECT
                    {ec.id_column},
                    {dimension_columns}
                FROM {ec.dimension_table}
                WHERE {ec.id_column} IN (SELECT {ec.id_column} FROM top_n)
                ORDER BY {ec.id_column}, updated_at DESC
                LIMIT 1 BY {ec.id_column}
            ),
            with_metadata AS (
                SELECT
                    t.user_id,
                    t.listen_count,
                    {select_fields}
                FROM top_n t
                LEFT JOIN dedup_metadata d ON t.{ec.id_column} = d.{ec.id_column}
                {self._entity_filter_clause()}
            )
            SELECT
                user_id,
                arrayMap(
                    x -> ({array_map_indices}),
                    arraySort(
                        x -> -x.1,
                        groupArray(tuple({tuple_fields}))
                    )
                ) AS entities
            FROM with_metadata
            GROUP BY user_id
            ORDER BY user_id
        """

    def stream_top_n_for_range(self, time_range: str, limit: int):
        """Yield (user_id, entity_tuples) rows from the top-N ranking for a time_range."""
        query = self.build_top_n_query(time_range)
        with self.ch_client.query_row_block_stream(
            query, parameters={"limit": limit}
        ) as stream:
            for block in stream:
                for row in block:
                    yield row[0], row[1]

    def _flush_user_batch(
        self,
        time_range: str,
        user_batch: dict,
        from_ts: int,
        to_ts: int,
        database: str,
        message_batch_size: int,
        max_created,
    ) -> Iterator[dict]:
        if not user_batch:
            return
        for msg in self.generate_stats_messages(
            time_range,
            user_batch,
            from_ts,
            to_ts,
            database=database,
            batch_size=message_batch_size,
        ):
            yield msg
        self.update_user_cache_state(list(user_batch.keys()), time_range, max_created)

    def run_bulk_full_refresh(
        self,
        message_batch_size: int = 100,
        user_flush_size: int = 5000,
    ) -> Iterator[dict]:
        """Stream a full refresh via one daily-table scan + per-time-range ranking.

        Yields RMQ messages in the same start / data / end pattern as
        StatsCacheManager.run_full_refresh so the LB-side CouchDB handler
        creates a fresh database per (entity, time_range).

        Args:
            message_batch_size: Users per outbound RMQ message.
            user_flush_size: Users to accumulate from the streaming result before
                emitting messages and updating cache state. Decouples ClickHouse
                block size from RMQ message size.
        """
        ec = self.entity_config
        logger.info("Starting bulk full refresh for %s...", ec.entity_type)

        self.drop_intermediate_table()
        try:
            t0 = time.perf_counter()
            self.build_intermediate_table()
            build_elapsed = time.perf_counter() - t0
            row_count = self.intermediate_row_count()
            logger.info(
                "Built intermediate %s (%d rows) in %.1fs",
                self.intermediate_table_name, row_count, build_elapsed,
            )

            if row_count == 0:
                logger.info(
                    "No rows in intermediate for %s; no stats databases will be created",
                    ec.entity_type,
                )
                return

            max_created = self.get_listen_max_created()
            total_messages = 0

            for time_range in TIME_RANGES:
                period_start, period_end = self.get_period_bounds(time_range)
                from_ts, to_ts = self.get_period_timestamps(time_range, period_start, period_end)

                database = self.get_stats_database_name(
                    ec.entity_type, time_range, with_timestamp=True,
                )

                yield self.generate_start_message(time_range, database)
                total_messages += 1

                self.clear_user_cache_state_for_time_range(time_range)

                user_batch: dict[int, list[dict]] = {}
                data_messages = 0
                stream_start = time.perf_counter()

                for user_id, entity_tuples in self.stream_top_n_for_range(
                    time_range, self.config.top_n,
                ):
                    user_batch[user_id] = [
                        _format_entity_tuple(t, ec.dimension_fields)
                        for t in entity_tuples
                    ]
                    if len(user_batch) >= user_flush_size:
                        for msg in self._flush_user_batch(
                            time_range, user_batch, from_ts, to_ts,
                            database, message_batch_size, max_created,
                        ):
                            yield msg
                            data_messages += 1
                            total_messages += 1
                        user_batch = {}

                for msg in self._flush_user_batch(
                    time_range, user_batch, from_ts, to_ts,
                    database, message_batch_size, max_created,
                ):
                    yield msg
                    data_messages += 1
                    total_messages += 1

                logger.info(
                    "  %s: %d data messages in %.1fs",
                    time_range, data_messages, time.perf_counter() - stream_start,
                )

                if data_messages > 0:
                    yield self.generate_end_message(time_range, database)
                    total_messages += 1

                self.update_cache_state(time_range, period_start, max_created)

            logger.info(
                "Bulk refresh for %s completed. %d messages generated",
                ec.entity_type, total_messages,
            )
        finally:
            self.drop_intermediate_table()
