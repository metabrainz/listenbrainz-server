#!/usr/bin/env python3
"""
Stats Cache Manager

Computes top 1000 entity stats (artists, recordings, release groups)
from ClickHouse and emits RabbitMQ result messages.

Architecture:
    - ClickHouse stores id-only listens and daily aggregated stats (user_{entity}_stats_daily)
    - MV automatically adds +1 for each new listen
    - Cache state tracked to only update affected users/time_ranges
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterator, Optional

import clickhouse_connect

from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

# Time range definitions
# "this_*" = current ongoing period, "*" alone = previous complete period
# period_end_sql: for ongoing periods use far future date, for complete periods use next boundary
TIME_RANGES = {
    'all_time': {
        'filter': '',
        'period_start_sql': "toDate('1970-01-01')",
        'period_end_sql': "toDate('2099-12-31')",
    },
    # Current ongoing periods (period_end = far future since they're open-ended)
    'this_week': {
        'filter': 'AND s.date >= toStartOfWeek(today())',
        'period_start_sql': 'toStartOfWeek(today())',
        'period_end_sql': "toDate('2099-12-31')",
    },
    'this_month': {
        'filter': 'AND s.date >= toStartOfMonth(today())',
        'period_start_sql': 'toStartOfMonth(today())',
        'period_end_sql': "toDate('2099-12-31')",
    },
    'this_year': {
        'filter': 'AND s.date >= toStartOfYear(today())',
        'period_start_sql': 'toStartOfYear(today())',
        'period_end_sql': "toDate('2099-12-31')",
    },
    # Previous complete periods (period_end = start of current period)
    'week': {
        'filter': 'AND s.date >= toStartOfWeek(today()) - 7 AND s.date < toStartOfWeek(today())',
        'period_start_sql': 'toStartOfWeek(today()) - 7',
        'period_end_sql': 'toStartOfWeek(today())',
    },
    'month': {
        'filter': 'AND s.date >= toStartOfMonth(today() - INTERVAL 1 MONTH) AND s.date < toStartOfMonth(today())',
        'period_start_sql': 'toStartOfMonth(today() - INTERVAL 1 MONTH)',
        'period_end_sql': 'toStartOfMonth(today())',
    },
    'quarter': {
        'filter': 'AND s.date >= toStartOfQuarter(today() - INTERVAL 3 MONTH) AND s.date < toStartOfQuarter(today())',
        'period_start_sql': 'toStartOfQuarter(today() - INTERVAL 3 MONTH)',
        'period_end_sql': 'toStartOfQuarter(today())',
    },
    'half_yearly': {
        'filter': '''AND s.date >= if(toMonth(today()) > 6,
                        toStartOfYear(today()),
                        toStartOfYear(today()) - INTERVAL 6 MONTH)
                     AND s.date < if(toMonth(today()) > 6,
                        toStartOfYear(today()) + INTERVAL 6 MONTH,
                        toStartOfYear(today()))''',
        'period_start_sql': '''if(toMonth(today()) > 6,
                                  toStartOfYear(today()),
                                  toStartOfYear(today()) - INTERVAL 6 MONTH)''',
        'period_end_sql': '''if(toMonth(today()) > 6,
                                toStartOfYear(today()) + INTERVAL 6 MONTH,
                                toStartOfYear(today()))''',
    },
    'year': {
        'filter': 'AND s.date >= toStartOfYear(today() - INTERVAL 1 YEAR) AND s.date < toStartOfYear(today())',
        'period_start_sql': 'toStartOfYear(today() - INTERVAL 1 YEAR)',
        'period_end_sql': 'toStartOfYear(today())',
    },
}

# Per-user cache state table schema
# Tracks when each user's cache was last computed for each time_range
USER_STATS_CACHE_STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_stats_cache_state (
    user_id UInt32,
    stat_type String,              -- 'artists', 'recordings', 'release_groups'
    time_range String,             -- 'all_time', 'this_week', etc.
    last_computed_created DateTime64(3),  -- max(created) from listens when cache was computed
    updated_at DateTime64(3) DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (user_id, stat_type, time_range)
"""

OPEN_ENDED_TIME_RANGES = {'all_time', 'this_week', 'this_month', 'this_year'}


def _identity(value: Any) -> Any:
    return value


def _json_array(value: Any) -> list[dict]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return decoded if isinstance(decoded, list) else []


def _non_empty_strings(value: Any) -> list[str]:
    return [item for item in (value or []) if item]


@dataclass(frozen=True)
class DimensionField:
    column: str
    output_key: str
    transform: Callable[[Any], Any] = _identity


@dataclass
class CacheConfig:
    """Configuration for cache manager."""
    ch_host: str = 'localhost'
    ch_port: int = 8123
    ch_database: str = 'default'
    ch_username: str = 'default'
    ch_password: str = ''
    top_n: int = 1000
    couch_db_prefix: str = 'clk'


@dataclass
class EntityConfig:
    """Configuration for a specific entity type."""
    entity_type: str  # 'artists', 'recordings', 'release_groups'
    stats_table: str  # e.g., 'user_artist_stats_daily'
    dimension_table: str  # e.g., 'artist_metadata'
    id_column: str  # e.g., 'artist_id'
    dimension_fields: list[DimensionField] = field(default_factory=list)


# Entity configurations for artists, recordings, and release groups
# Artist uses unified artist_id: MB ID (small) for mapped, hash (large) for unmapped
ARTIST_CONFIG = EntityConfig(
    entity_type='artists',
    stats_table='user_artist_stats_daily',
    dimension_table='artist_metadata',
    id_column='artist_id',  # Unified ID: MB ID or hash
    dimension_fields=[
        DimensionField('artist_mbid', 'artist_mbid'),
        DimensionField('artist_name', 'artist_name'),
    ],
)

RECORDING_CONFIG = EntityConfig(
    entity_type='recordings',
    stats_table='user_recording_stats_daily',
    dimension_table='recording_metadata',
    id_column='recording_id',
    dimension_fields=[
        DimensionField('recording_mbid', 'recording_mbid'),
        DimensionField('recording_name', 'track_name'),
        DimensionField('artist_name', 'artist_name'),
        DimensionField('artist_credit_mbids', 'artist_mbids', _non_empty_strings),
        DimensionField('release_name', 'release_name'),
        DimensionField('release_mbid', 'release_mbid'),
        DimensionField('artists', 'artists', _json_array),
        DimensionField('caa_id', 'caa_id'),
        DimensionField('caa_release_mbid', 'caa_release_mbid'),
    ],
)

RELEASE_GROUP_CONFIG = EntityConfig(
    entity_type='release_groups',
    stats_table='user_release_group_stats_daily',
    dimension_table='release_group_metadata',
    id_column='release_group_id',
    dimension_fields=[
        DimensionField('release_group_mbid', 'release_group_mbid'),
        DimensionField('release_group_name', 'release_group_name'),
        DimensionField('artist_name', 'artist_name'),
        DimensionField('artist_credit_mbids', 'artist_mbids', _non_empty_strings),
        DimensionField('artists', 'artists', _json_array),
        DimensionField('caa_id', 'caa_id'),
        DimensionField('caa_release_mbid', 'caa_release_mbid'),
    ],
)

ENTITY_CONFIGS = {
    'artists': ARTIST_CONFIG,
    'recordings': RECORDING_CONFIG,
    'release_groups': RELEASE_GROUP_CONFIG,
}

def _to_utc_timestamp(value: date | datetime) -> int:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.combine(value, datetime.min.time())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _format_entity_tuple(entity_tuple: tuple, dimension_fields: list[DimensionField]) -> dict:
    entity = {
        field.output_key: field.transform(value)
        for field, value in zip(dimension_fields, entity_tuple[:-1], strict=True)
    }
    entity['listen_count'] = entity_tuple[-1]
    return entity


def get_cache_config_from_config(config_module) -> CacheConfig:
    """Create CacheConfig from a config module."""
    return CacheConfig(
        ch_host=getattr(config_module, 'CLICKHOUSE_HOST', 'localhost'),
        ch_port=getattr(config_module, 'CLICKHOUSE_PORT', 8123),
        ch_database=getattr(config_module, 'CLICKHOUSE_DATABASE', 'default'),
        ch_username=getattr(config_module, 'CLICKHOUSE_USERNAME', 'default'),
        ch_password=getattr(config_module, 'CLICKHOUSE_PASSWORD', ''),
        top_n=getattr(config_module, 'STATS_TOP_N', 1000),
        couch_db_prefix=getattr(config_module, 'STATS_COUCH_DB_PREFIX', 'clk'),
    )


class StatsCacheManager:
    """Manages ClickHouse stats computation and RabbitMQ result messages."""

    def __init__(self, config: CacheConfig, entity_config: EntityConfig):
        self.config = config
        self.entity_config = entity_config
        self.ch_client = None

    def connect(self):
        """Establish a connection to ClickHouse."""
        self.ch_client = clickhouse_connect.get_client(
            host=self.config.ch_host,
            port=self.config.ch_port,
            database=self.config.ch_database,
            username=self.config.ch_username,
            password=self.config.ch_password,
            form_encode_query_params=True,
        )
        logger.info(f"Connected to ClickHouse at {self.config.ch_host}:{self.config.ch_port}")

        # Ensure required tables exist
        ensure_stats_schema(self.ch_client)
        self.ch_client.command(USER_STATS_CACHE_STATE_SCHEMA)

    def get_stats_database_name(self, entity_type: str, time_range: str, with_timestamp: bool = False) -> str:
        """
        Generate ClickHouse stats database name for entity type and time range.

        Args:
            entity_type: The entity type (artists, recordings, release_groups)
            time_range: The time range (all_time, this_week, etc.)
            with_timestamp: If True, append YYYYMMDD timestamp for new database creation

        Returns:
            Database name like 'clk_artists_all_time' or 'clk_artists_all_time_20240115'
        """
        db_name = self.get_stats_database_prefix(entity_type, time_range)

        if with_timestamp:
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
            db_name = f"{db_name}_{timestamp}"

        return db_name

    def get_stats_database_prefix(self, entity_type: str, time_range: str) -> str:
        """Get ClickHouse stats database prefix for finding the current CouchDB database."""
        return f"{self.config.couch_db_prefix}_{entity_type}_{time_range}"

    def get_cache_state(self) -> dict[str, dict]:
        """Get current cache state for all time ranges."""
        stat_type = self.entity_config.entity_type
        state_query = """
            SELECT time_range, last_computed, period_start
            FROM stats_cache_state FINAL
            WHERE stat_type = {stat_type:String}
        """
        result = self.ch_client.query(state_query, parameters={'stat_type': stat_type})
        return {row[0]: {'last_computed': row[1], 'period_start': row[2]} for row in result.result_rows}

    def get_stale_users(
        self,
        time_range: str,
        period_start,
        period_end,
    ) -> list[int]:
        """
        Get users needing cache update using per-user cache state.

        Uses EXISTS pattern for optimal query performance:
        1. Users with no cache state for this time_range (never computed)
        2. Users with new listens (created > last_computed_created) within period bounds
        Args:
            time_range: The time range to check
            period_start: Start date of the period
            period_end: End date of the period (exclusive)

        Returns:
            List of user_ids needing update
        """
        stat_type = self.entity_config.entity_type
        stats_table = self.entity_config.stats_table
        # Query finds:
        # 1. Users who have stats but no cache state (never computed for this range)
        # 2. Users whose cache is stale (new listens within period since last compute)
        query = f"""
            WITH cached_users AS (
                SELECT user_id, last_computed_created
                FROM user_stats_cache_state FINAL
                WHERE stat_type = {{stat_type:String}}
                  AND time_range = {{time_range:String}}
            )
            SELECT DISTINCT user_id FROM (
                -- Users with stats but never cached for this time_range
                SELECT DISTINCT s.user_id
                FROM {stats_table} s
                WHERE NOT EXISTS (
                    SELECT 1 FROM cached_users c WHERE c.user_id = s.user_id
                )

                UNION ALL

                -- Users with new listens within period since last compute
                SELECT c.user_id
                FROM cached_users c
                WHERE EXISTS (
                    SELECT 1 FROM listens l
                    WHERE l.user_id = c.user_id
                      AND l.created > c.last_computed_created
                      AND toDate(l.listened_at) >= {{period_start:Date}}
                      AND toDate(l.listened_at) < {{period_end:Date}}
                )
            )
        """
        ch_start = time.perf_counter()
        result = self.ch_client.query(query, parameters={
            'stat_type': stat_type,
            'time_range': time_range,
            'period_start': period_start,
            'period_end': period_end,
        })
        ch_elapsed = time.perf_counter() - ch_start
        logger.info(f"Stale users query took {ch_elapsed:.2f}s")

        return [row[0] for row in result.result_rows]

    def get_listen_max_created(self):
        """Get the maximum created timestamp from listens table."""
        result = self.ch_client.query("SELECT max(created) FROM listens")
        return result.result_rows[0][0]

    def check_period_rollover(self, time_range: str, cached_period_start) -> bool:
        """Check if the period boundary has changed for a time_range."""
        if time_range == 'all_time':
            return False

        config = TIME_RANGES.get(time_range)
        if not config:
            return False

        current_period_result = self.ch_client.query(f"SELECT {config['period_start_sql']}")
        current_period_start = current_period_result.first_row[0]

        return cached_period_start != current_period_start

    def get_period_bounds(self, time_range: str) -> tuple:
        """Get the current period start and end dates for a time_range."""
        config = TIME_RANGES.get(time_range, {
            'period_start_sql': "toDate('1970-01-01')",
            'period_end_sql': "toDate('2099-12-31')"
        })
        result = self.ch_client.query(
            f"SELECT {config['period_start_sql']}, {config['period_end_sql']}"
        )
        return result.first_row[0], result.first_row[1]

    def get_period_timestamps(self, time_range: str, period_start, period_end) -> tuple[int, int]:
        """Return API from/to timestamps for a stats range."""
        from_ts = _to_utc_timestamp(period_start)
        if time_range in OPEN_ENDED_TIME_RANGES:
            to_ts = int(datetime.now(tz=timezone.utc).timestamp())
        else:
            to_ts = _to_utc_timestamp(period_end)
        return from_ts, to_ts

    def on_period_rollover(
        self,
        time_range: str,
        old_period_start,
        new_period_start,
    ):
        """
        Called when a period rollover is detected for a time_range.

        Args:
            time_range: The time range that rolled over (e.g., 'this_week')
            old_period_start: The previous period start date
            new_period_start: The new/current period start date
        """
        logger.info(
            f"Period rollover for {time_range}: {old_period_start} -> {new_period_start}. "
            "User cache state will be cleared and a new stats database will be requested."
        )

    def _build_select_fields(self) -> str:
        """Build SELECT clause for dimension fields."""
        fields = []
        for dim_field in self.entity_config.dimension_fields:
            fields.append(f'd.{dim_field.column}')
        return ', '.join(fields)

    def _build_dimension_columns(self) -> str:
        """Comma-separated raw column names for the dimension dedup subquery."""
        return ', '.join(dim_field.column for dim_field in self.entity_config.dimension_fields)

    def _build_tuple_fields(self) -> str:
        """Build tuple fields for groupArray."""
        fields = ['listen_count']
        for dim_field in self.entity_config.dimension_fields:
            dim_col = dim_field.column
            if dim_col.endswith('_mbid') and dim_col != 'artist_credit_mbids':
                fields.append(f"nullIf({dim_col}, '')")
            else:
                fields.append(dim_col)
        return ', '.join(fields)

    def _build_array_map_indices(self) -> str:
        """Build arrayMap tuple indices to reorder: move listen_count to end."""
        num_fields = len(self.entity_config.dimension_fields) + 1
        indices = [f'x.{i+2}' for i in range(len(self.entity_config.dimension_fields))]
        indices.append('x.1')
        return ', '.join(indices)

    def compute_top_entities_batch(
        self,
        time_range: str,
        user_ids: list[int],
        limit: int = 1000
    ) -> dict[int, list[dict]]:
        """Compute top N entities for multiple users in a single query."""
        if not user_ids:
            return {}

        range_config = TIME_RANGES.get(time_range, {'filter': '', 'period_start_sql': "toDate('1970-01-01')"})

        date_filter = range_config['filter']

        ec = self.entity_config
        select_fields = self._build_select_fields()
        dimension_columns = self._build_dimension_columns()
        tuple_fields = self._build_tuple_fields()
        array_map_indices = self._build_array_map_indices()

        # Dedup the ReplacingMergeTree dimension table via ORDER BY ... LIMIT 1 BY
        # instead of FINAL: FINAL triggers a runtime merge across all parts and runs
        # once per query, while LIMIT 1 BY does a single sort over a pre-filtered slice.
        query = f"""
            WITH aggregated AS (
                SELECT
                    user_id,
                    {ec.id_column},
                    sum(listen_count) AS listen_count
                FROM {ec.stats_table} s
                WHERE user_id IN ({{user_ids:Array(UInt32)}})
                {date_filter}
                GROUP BY user_id, {ec.id_column}
                HAVING listen_count > 0
            ),
            ranked AS (
                SELECT
                    user_id,
                    {ec.id_column},
                    listen_count,
                    row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rn
                FROM aggregated
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
            )
            SELECT
                user_id,
                arrayMap(
                    x -> ({array_map_indices}),
                    arraySort(
                        x -> -x.1,
                        groupArray(
                            tuple({tuple_fields})
                        )
                    )
                ) AS entities
            FROM with_metadata
            GROUP BY user_id
            ORDER BY user_id
        """

        ch_start = time.perf_counter()
        result = self.ch_client.query(
            query,
            parameters={'user_ids': user_ids, 'limit': limit}
        )
        ch_elapsed = time.perf_counter() - ch_start
        logger.info(f"ClickHouse query took {ch_elapsed:.2f}s for {len(user_ids)} users")

        user_entities: dict[int, list[dict]] = {uid: [] for uid in user_ids}

        for row in result.result_rows:
            user_id, entities_tuples = row
            user_entities[user_id] = [
                _format_entity_tuple(entity_tuple, self.entity_config.dimension_fields)
                for entity_tuple in entities_tuples
            ]

        return user_entities

    def generate_start_message(self, time_range: str, database: str) -> dict:
        """
        Generate a start message for a new stats database.

        This message signals the LB handler to create a new database
        for incoming stats data.

        Args:
            time_range: The time range for these stats
            database: The full database name with timestamp

        Returns:
            Start message dict
        """
        entity_type = self.entity_config.entity_type
        return {
            'type': 'clk_stats_database_start',
            'entity_type': entity_type,
            'time_range': time_range,
            'database': database,
        }

    def generate_end_message(self, time_range: str, database: str) -> dict:
        """
        Generate an end message to finalize stats database.

        This message signals the LB handler to cleanup old databases
        of the same type.

        Args:
            time_range: The time range for these stats
            database: The full database name with timestamp

        Returns:
            End message dict
        """
        entity_type = self.entity_config.entity_type
        return {
            'type': 'clk_stats_database_end',
            'entity_type': entity_type,
            'time_range': time_range,
            'database': database,
        }

    def generate_stats_messages(
        self,
        time_range: str,
        user_results: dict[int, list[dict]],
        from_ts: int,
        to_ts: int,
        database: str | None = None,
        database_prefix: str | None = None,
        batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Generate batched RMQ messages for stats data.

        Stats are batched to reduce RMQ message count while keeping
        individual message sizes manageable.

        Args:
            time_range: The time range for these stats
            user_results: Dict mapping user_id to their stats list
            from_ts: Start timestamp for this stats range
            to_ts: End timestamp for this stats range
            database: The exact database name to insert into
            database_prefix: Prefix used by LB to select the latest stats database
            batch_size: Number of users per message batch

        Yields:
            Messages to send via RMQ
        """
        entity_type = self.entity_config.entity_type

        # Convert to list of (user_id, stats) for batching
        items = list(user_results.items())

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            # Format batch as list of user stat dicts
            batch_data = []
            for user_id, stats in batch:
                batch_data.append({
                    'user_id': user_id,
                    'count': len(stats),
                    'data': stats,
                })

            message = {
                'type': 'clk_user_entity',
                'entity': entity_type,
                'stats_range': time_range,
                'from_ts': from_ts,
                'to_ts': to_ts,
                'data': batch_data,
            }
            if database is not None:
                message['database'] = database
            if database_prefix is not None:
                message['database_prefix'] = database_prefix
            yield message

    def update_cache_state(
        self,
        time_range: str,
        period_start,
        last_computed: datetime,
    ):
        """Update the global cache state for a time_range."""
        stat_type = self.entity_config.entity_type
        self.ch_client.command("""
            INSERT INTO stats_cache_state
                (stat_type, time_range, last_computed, period_start)
            VALUES
                ({stat_type:String}, {time_range:String}, {last_computed:DateTime64(3)}, {period_start:Date})
        """, parameters={
            'stat_type': stat_type,
            'time_range': time_range,
            'last_computed': last_computed,
            'period_start': period_start,
        })

    def update_user_cache_state(
        self,
        user_ids: list[int],
        time_range: str,
        max_created: datetime,
    ):
        """Batch update per-user cache state after computing their stats."""
        if not user_ids:
            return

        stat_type = self.entity_config.entity_type

        rows = [
            (uid, stat_type, time_range, max_created)
            for uid in user_ids
        ]

        self.ch_client.insert(
            'user_stats_cache_state',
            rows,
            column_names=[
                'user_id', 'stat_type', 'time_range', 'last_computed_created',
            ]
        )
        logger.debug(f"Updated cache state for {len(user_ids)} users")

    def clear_user_cache_state_for_time_range(
        self,
        time_range: str,
    ):
        """Clear all user cache state for a time_range (e.g., on period rollover)."""
        stat_type = self.entity_config.entity_type
        self.ch_client.command("""
            ALTER TABLE user_stats_cache_state
            DELETE WHERE stat_type = {stat_type:String} AND time_range = {time_range:String}
        """, parameters={
            'stat_type': stat_type,
            'time_range': time_range,
        })
        logger.info(f"Cleared user cache state for {stat_type}/{time_range}")

    def refresh_time_range_batch(
        self,
        time_range: str,
        user_ids: list[int],
        from_ts: int,
        to_ts: int,
        database: str | None = None,
        database_prefix: str | None = None,
        message_batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Compute stats for multiple users and yield RMQ messages.

        Args:
            time_range: The time range to compute stats for
            user_ids: List of user IDs to process
            from_ts: Start timestamp for this stats range
            to_ts: End timestamp for this stats range
            database: The exact database name to include in messages
            database_prefix: Prefix used by LB to select the latest stats database
            message_batch_size: Number of users per RMQ message

        Yields:
            RabbitMQ messages with stats data
        """
        if not user_ids:
            return

        user_entities = self.compute_top_entities_batch(time_range, user_ids, self.config.top_n)

        total_entities = sum(len(e) for e in user_entities.values())
        entity_type = self.entity_config.entity_type
        logger.info(f"  {time_range}: {len(user_ids)} users, {total_entities} total {entity_type}s computed")

        yield from self.generate_stats_messages(
            time_range,
            user_entities,
            from_ts,
            to_ts,
            database=database,
            database_prefix=database_prefix,
            batch_size=message_batch_size,
        )

    def run_hourly_job(
        self,
        batch_size: int = 1000,
        message_batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Run the hourly job and yield RabbitMQ result messages.

        For each time_range:
        - If period rollover detected: yield start/data/end messages (new database)
        - Otherwise: yield data messages only (append to existing database)

        Message flow for rollover:
        1. clk_stats_database_start - create new database
        2. clk_user_entity (batched) - stats data
        3. clk_stats_database_end - cleanup old databases

        Yields:
            RabbitMQ messages with stats data
        """
        entity_type = self.entity_config.entity_type
        logger.info(f"Starting hourly job for {entity_type}...")

        cache_state = self.get_cache_state()

        total_users_processed = 0
        total_messages = 0

        for time_range, config in TIME_RANGES.items():
            state = cache_state.get(time_range, {})
            cached_period_start = state.get('period_start')

            period_start, period_end = self.get_period_bounds(time_range)
            from_ts, to_ts = self.get_period_timestamps(time_range, period_start, period_end)

            # Check for period rollover
            is_rollover = cached_period_start is not None and cached_period_start != period_start
            if is_rollover:
                logger.info(f"{time_range}: period rollover detected ({cached_period_start} -> {period_start})")
                self.on_period_rollover(time_range, cached_period_start, period_start)
                self.clear_user_cache_state_for_time_range(time_range)

            stale_users = self.get_stale_users(time_range, period_start, period_end)

            if not stale_users:
                logger.info(f"{time_range}: no stale users")
                continue

            logger.info(f"{time_range}: computing stats for {len(stale_users)} users")

            # For rollover, create new database with timestamp; otherwise use existing
            if is_rollover:
                database = self.get_stats_database_name(entity_type, time_range, with_timestamp=True)
                database_prefix = None
                # Yield start message for new database
                yield self.generate_start_message(time_range, database)
                total_messages += 1
            else:
                database = None
                database_prefix = self.get_stats_database_prefix(entity_type, time_range)

            max_created = self.get_listen_max_created()
            time_range_message_count = 0

            for i in range(0, len(stale_users), batch_size):
                batch = stale_users[i:i + batch_size]
                try:
                    for message in self.refresh_time_range_batch(
                        time_range,
                        batch,
                        from_ts,
                        to_ts,
                        database=database,
                        database_prefix=database_prefix,
                        message_batch_size=message_batch_size,
                    ):
                        yield message
                        time_range_message_count += 1
                        total_messages += 1
                    self.update_user_cache_state(batch, time_range, max_created)
                    total_users_processed += len(batch)
                except Exception as e:
                    logger.error(f"Error computing {time_range} batch {i}: {e}")

            # For rollover, yield end message to cleanup old databases
            if is_rollover and time_range_message_count > 0:
                yield self.generate_end_message(time_range, database)
                total_messages += 1

            if stale_users:
                self.update_cache_state(time_range, period_start, max_created)

        logger.info(
            "Hourly job for %s completed. Computed %d user/time_range combinations, %d messages",
            entity_type,
            total_users_processed,
            total_messages,
        )

    def run_full_refresh(
        self,
        batch_size: int = 1000,
        message_batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Run full refresh and yield RabbitMQ result messages.

        Full refresh always creates new databases with timestamps for all time_ranges.

        Message flow for each time_range:
        1. clk_stats_database_start - create new database
        2. clk_user_entity (batched) - stats data
        3. clk_stats_database_end - cleanup old databases

        Args:
            batch_size: Number of users to process per ClickHouse query batch
            message_batch_size: Number of users per RMQ message

        Yields:
            RabbitMQ messages with stats data
        """
        entity_type = self.entity_config.entity_type
        stats_table = self.entity_config.stats_table
        logger.info(f"Starting full refresh for {entity_type}...")

        result = self.ch_client.query(f"""
            SELECT DISTINCT user_id FROM {stats_table}
        """)

        all_users = [row[0] for row in result.result_rows]
        logger.info(f"Found {len(all_users)} users to refresh")
        if not all_users:
            logger.info("No users found for %s full refresh; no stats databases will be created", entity_type)
            return

        total_messages = 0

        for time_range in TIME_RANGES:
            logger.info(f"Processing {time_range}...")

            period_start, period_end = self.get_period_bounds(time_range)
            from_ts, to_ts = self.get_period_timestamps(time_range, period_start, period_end)
            max_created = self.get_listen_max_created()

            # Full refresh always creates new database with timestamp
            database = self.get_stats_database_name(entity_type, time_range, with_timestamp=True)

            # Yield start message for new database
            yield self.generate_start_message(time_range, database)
            total_messages += 1

            # Clear user cache state since we're doing a full refresh
            self.clear_user_cache_state_for_time_range(time_range)

            time_range_message_count = 0
            for i in range(0, len(all_users), batch_size):
                batch = all_users[i:i + batch_size]
                try:
                    for message in self.refresh_time_range_batch(
                        time_range,
                        batch,
                        from_ts,
                        to_ts,
                        database=database,
                        message_batch_size=message_batch_size,
                    ):
                        yield message
                        time_range_message_count += 1
                        total_messages += 1
                    self.update_user_cache_state(batch, time_range, max_created)
                    logger.info(f"  Progress: {min(i + batch_size, len(all_users))}/{len(all_users)} users")
                except Exception as e:
                    logger.error(f"Error batch computing {time_range} batch {i}: {e}")

            # Yield end message to cleanup old databases
            if time_range_message_count > 0:
                yield self.generate_end_message(time_range, database)
                total_messages += 1

            self.update_cache_state(time_range, period_start, max_created)

        logger.info(f"Full refresh for {entity_type} completed. {total_messages} messages generated")
