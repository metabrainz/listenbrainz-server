#!/usr/bin/env python3
"""
Stats Cache Manager

Manages the caching of top 1000 entity stats (artists, recordings, release groups)
in CouchDB with smart invalidation.

Architecture:
    - ClickHouse stores daily aggregated stats (user_{entity}_stats_daily)
    - MV automatically adds +1 for each new listen
    - Deletions logged to deleted_listens_log, processed hourly as -1
    - CouchDB caches computed top 1000 per user/entity/time_range
    - Cache state tracked to only update affected users/time_ranges
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator, Optional

import clickhouse_connect
import orjson
import requests

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
    stat_type String,              -- 'artist', 'recording', 'release_group'
    time_range String,             -- 'all_time', 'this_week', etc.
    last_computed_created DateTime64(3),  -- max(created) from listens when cache was computed
    updated_at DateTime64(3) DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (user_id, stat_type, time_range)
"""

# Unified deletion log table schema for all entity types
# When a listen is deleted, it affects artist, recording, and release_group stats
DELETED_LISTENS_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS deleted_listens_log (
    user_id UInt32,
    date Date,
    listened_at DateTime64(3),
    artist_id UInt64,
    recording_id UInt64,
    release_group_id UInt64,
    processed UInt8 DEFAULT 0,
    deleted_at DateTime64(3) DEFAULT now64(3)
) ENGINE = MergeTree()
ORDER BY (user_id, date, deleted_at)
"""


@dataclass
class CacheConfig:
    """Configuration for cache manager."""
    ch_host: str = 'localhost'
    ch_port: int = 8123
    ch_database: str = 'default'
    ch_username: str = 'default'
    ch_password: str = ''
    couch_host: str = 'localhost'
    couch_port: int = 5984
    couch_username: str = 'admin'
    couch_password: str = ''
    couch_db_prefix: str = ''  # Optional prefix for database names
    couch_workers: int = 3  # Number of threads for CouchDB inserts
    top_n: int = 1000


@dataclass
class EntityConfig:
    """Configuration for a specific entity type (artist, recording, release_group)."""
    entity_type: str  # 'artist', 'recording', 'release_group'
    stats_table: str  # e.g., 'user_artist_stats_daily'
    dimension_table: str  # e.g., 'artist_dim'
    id_column: str  # e.g., 'artist_id'
    # List of (dim_column, output_key) tuples for dimension table fields
    # output_key is the name used in the output dict (may differ from dim_column)
    dimension_fields: list[tuple[str, str]] = field(default_factory=list)


# Entity configurations for artists, recordings, and release groups
ARTIST_CONFIG = EntityConfig(
    entity_type='artist',
    stats_table='user_artist_stats_daily',
    dimension_table='artist_dim',
    id_column='artist_id',
    dimension_fields=[
        ('artist_mbid', 'artist_mbid'),
        ('artist_name', 'artist_name'),
    ],
)

RECORDING_CONFIG = EntityConfig(
    entity_type='recording',
    stats_table='user_recording_stats_daily',
    dimension_table='recording_dim',
    id_column='recording_id',
    dimension_fields=[
        ('recording_mbid', 'recording_mbid'),
        ('recording_name', 'track_name'),  # Output as 'track_name' per data model
        ('artist_name', 'artist_name'),
        ('artist_credit_mbids', 'artist_mbids'),  # Output as 'artist_mbids' per data model
        ('release_name', 'release_name'),
        ('release_mbid', 'release_mbid'),
        ('artists', 'artists'),
        ('caa_id', 'caa_id'),
        ('caa_release_mbid', 'caa_release_mbid'),
    ],
)

RELEASE_GROUP_CONFIG = EntityConfig(
    entity_type='release_group',
    stats_table='user_release_group_stats_daily',
    dimension_table='release_group_dim',
    id_column='release_group_id',
    dimension_fields=[
        ('release_group_mbid', 'release_group_mbid'),
        ('release_group_name', 'release_group_name'),
        ('artist_name', 'artist_name'),
        ('artist_credit_mbids', 'artist_mbids'),  # Output as 'artist_mbids' per data model
        ('artists', 'artists'),
        ('caa_id', 'caa_id'),
        ('caa_release_mbid', 'caa_release_mbid'),
    ],
)

ENTITY_CONFIGS = {
    'artist': ARTIST_CONFIG,
    'recording': RECORDING_CONFIG,
    'release_group': RELEASE_GROUP_CONFIG,
}


def get_cache_config_from_config(config_module) -> CacheConfig:
    """Create CacheConfig from a config module."""
    return CacheConfig(
        ch_host=getattr(config_module, 'CLICKHOUSE_HOST', 'localhost'),
        ch_port=getattr(config_module, 'CLICKHOUSE_PORT', 8123),
        ch_database=getattr(config_module, 'CLICKHOUSE_DATABASE', 'default'),
        ch_username=getattr(config_module, 'CLICKHOUSE_USERNAME', 'default'),
        ch_password=getattr(config_module, 'CLICKHOUSE_PASSWORD', ''),
        couch_host=getattr(config_module, 'COUCHDB_HOST', 'localhost'),
        couch_port=getattr(config_module, 'COUCHDB_PORT', 5984),
        couch_username=getattr(config_module, 'COUCHDB_USER', 'admin'),
        couch_password=getattr(config_module, 'COUCHDB_ADMIN_KEY', ''),
        couch_db_prefix=getattr(config_module, 'STATS_COUCH_DB_PREFIX', ''),
        couch_workers=getattr(config_module, 'STATS_COUCH_WORKERS', 3),
        top_n=getattr(config_module, 'STATS_TOP_N', 1000),
    )


class StatsCacheManager:
    """Manages entity stats caching between ClickHouse and CouchDB."""

    def __init__(self, config: CacheConfig, entity_config: EntityConfig):
        self.config = config
        self.entity_config = entity_config
        self.ch_client = None
        self.couch_base_url = None

    def connect(self):
        """Establish connections to ClickHouse and CouchDB."""
        # ClickHouse
        self.ch_client = clickhouse_connect.get_client(
            host=self.config.ch_host,
            port=self.config.ch_port,
            database=self.config.ch_database,
            username=self.config.ch_username,
            password=self.config.ch_password,
        )
        logger.info(f"Connected to ClickHouse at {self.config.ch_host}:{self.config.ch_port}")

        # Ensure required tables exist
        self.ch_client.command(USER_STATS_CACHE_STATE_SCHEMA)
        self.ch_client.command(DELETED_LISTENS_LOG_SCHEMA)

        # CouchDB base URL with auth
        self.couch_base_url = (
            f"http://{self.config.couch_username}:{self.config.couch_password}"
            f"@{self.config.couch_host}:{self.config.couch_port}"
        )
        logger.info(f"CouchDB configured at {self.config.couch_host}:{self.config.couch_port}")

    def get_couch_db_name(self, entity_type: str, time_range: str, with_timestamp: bool = False) -> str:
        """
        Generate CouchDB database name for entity type and time range.

        Args:
            entity_type: The entity type (artist, recording, release_group)
            time_range: The time range (all_time, this_week, etc.)
            with_timestamp: If True, append YYYYMMDD timestamp for new database creation

        Returns:
            Database name like 'clk_artist_all_time' or 'clk_artist_all_time_20240115'
        """
        base_name = f"{entity_type}_{time_range}"
        if self.config.couch_db_prefix:
            db_name = f"{self.config.couch_db_prefix}_{base_name}"
        else:
            db_name = base_name

        if with_timestamp:
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
            db_name = f"{db_name}_{timestamp}"

        return db_name

    def get_couch_db_prefix(self, entity_type: str, time_range: str) -> str:
        """Get database prefix for listing/deleting old databases."""
        base_name = f"{entity_type}_{time_range}"
        if self.config.couch_db_prefix:
            return f"{self.config.couch_db_prefix}_{base_name}"
        return base_name

    def create_couch_db(self, db_name: str) -> bool:
        """Create a CouchDB database. Returns True if created, False if already exists."""
        url = f"{self.couch_base_url}/{db_name}"
        response = requests.put(url)
        if response.status_code == 201:
            logger.info(f"Created CouchDB database: {db_name}")
            return True
        elif response.status_code == 412:  # Already exists
            return False
        response.raise_for_status()
        return False

    def delete_couch_db(self, db_name: str) -> bool:
        """Delete a CouchDB database. Returns True if deleted."""
        url = f"{self.couch_base_url}/{db_name}"
        response = requests.delete(url)
        if response.status_code == 200:
            logger.info(f"Deleted CouchDB database: {db_name}")
            return True
        elif response.status_code == 404:  # Doesn't exist
            return False
        response.raise_for_status()
        return False

    def get_deletion_cutoff(self) -> Optional[datetime]:
        """
        Get the current max deleted_at timestamp from pending deletions.

        This should be captured before processing starts to avoid race conditions
        where new deletions inserted during processing would be incorrectly marked
        as processed.

        Returns:
            The max deleted_at timestamp, or None if no pending deletions.
        """
        result = self.ch_client.query("""
            SELECT max(deleted_at) FROM deleted_listens_log WHERE processed = 0
        """)
        max_deleted_at = result.first_row[0]
        # ClickHouse returns epoch (1970-01-01) for max() of empty set
        if max_deleted_at is None or max_deleted_at.year == 1970:
            return None
        return max_deleted_at

    def process_deletions(self, cutoff: Optional[datetime] = None) -> int:
        """
        Process pending deletions from deleted_listens_log.
        Inserts negative counts into the stats table for this entity type.

        Args:
            cutoff: Only process deletions with deleted_at <= this timestamp.
                   If None, processes all pending deletions (not recommended due to race conditions).

        Returns:
            Number of deletions processed.
        """
        entity_type = self.entity_config.entity_type
        stats_table = self.entity_config.stats_table
        id_column = self.entity_config.id_column

        logger.info(f"Processing pending deletions for {entity_type}...")

        # Build cutoff filter
        cutoff_filter = ""
        params = {}
        if cutoff is not None:
            cutoff_filter = "AND deleted_at <= {cutoff:DateTime64(3)}"
            params['cutoff'] = cutoff

        # Count pending deletions that have a valid entity ID for this type
        count_result = self.ch_client.query(f"""
            SELECT count() FROM deleted_listens_log
            WHERE processed = 0 AND {id_column} != 0 {cutoff_filter}
        """, parameters=params)
        pending_count = count_result.first_row[0]

        if pending_count == 0:
            logger.info(f"No pending deletions to process for {entity_type}")
            return 0

        logger.info(f"Processing {pending_count} pending deletions for {entity_type}")

        # Insert negative counts for this entity type
        self.ch_client.command(f"""
            INSERT INTO {stats_table} (date, user_id, {id_column}, listen_count)
            SELECT
                date,
                user_id,
                {id_column},
                -toInt64(count()) AS listen_count
            FROM deleted_listens_log
            WHERE processed = 0 AND {id_column} != 0 {cutoff_filter}
            GROUP BY date, user_id, {id_column}
        """, parameters=params)

        logger.info(f"Processed {pending_count} deletions for {entity_type}")
        return pending_count

    def mark_deletions_processed(self, cutoff: Optional[datetime] = None):
        """
        Mark pending deletions as processed up to a cutoff timestamp.

        This should be called after all entity types have processed their deletions.

        Args:
            cutoff: Only mark deletions with deleted_at <= this timestamp.
                   If None, marks all pending deletions (not recommended due to race conditions).
        """
        if cutoff is not None:
            self.ch_client.command("""
                ALTER TABLE deleted_listens_log
                UPDATE processed = 1
                WHERE processed = 0 AND deleted_at <= {cutoff:DateTime64(3)}
            """, parameters={'cutoff': cutoff})
        else:
            self.ch_client.command("""
                ALTER TABLE deleted_listens_log
                UPDATE processed = 1 WHERE processed = 0
            """)

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
        3. Users with deletions since last compute

        Args:
            time_range: The time range to check
            period_start: Start date of the period
            period_end: End date of the period (exclusive)

        Returns:
            List of user_ids needing update
        """
        stat_type = self.entity_config.entity_type
        stats_table = self.entity_config.stats_table
        id_column = self.entity_config.id_column

        # Build deletion check subquery for this entity type
        deletion_check = f"""
            UNION ALL

            -- Users with deletions since last compute
            SELECT c.user_id
            FROM cached_users c
            WHERE EXISTS (
                SELECT 1 FROM deleted_listens_log d
                WHERE d.user_id = c.user_id
                  AND d.deleted_at > c.last_computed_created
                  AND d.date >= {{period_start:Date}}
                  AND d.date < {{period_end:Date}}
                  AND d.{id_column} != 0
            )
        """

        # Query finds:
        # 1. Users who have stats but no cache state (never computed for this range)
        # 2. Users whose cache is stale (new listens within period since last compute)
        # 3. Users with deletions affecting this period
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
                {deletion_check}
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
        entity_type = self.entity_config.entity_type
        db_name = self.get_couch_db_name(entity_type, time_range)
        logger.info(
            f"Period rollover for {time_range}: {old_period_start} -> {new_period_start}. "
            f"Database '{db_name}' should be cleared."
        )
        # TODO: Implement cache cleanup

    def _build_select_fields(self) -> str:
        """Build SELECT clause for dimension fields."""
        fields = []
        for dim_col, _ in self.entity_config.dimension_fields:
            fields.append(f'd.{dim_col}')
        return ', '.join(fields)

    def _build_tuple_fields(self) -> str:
        """Build tuple fields for groupArray."""
        fields = ['listen_count']
        for dim_col, _ in self.entity_config.dimension_fields:
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
        tuple_fields = self._build_tuple_fields()
        array_map_indices = self._build_array_map_indices()

        query = f"""
            WITH aggregated AS (
                SELECT
                    user_id,
                    {ec.id_column},
                    sum(listen_count) AS listen_count
                FROM {ec.stats_table}
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
            with_metadata AS (
                SELECT
                    t.user_id,
                    t.listen_count,
                    {select_fields}
                FROM top_n t
                JOIN {ec.dimension_table} d FINAL ON t.{ec.id_column} = d.{ec.id_column}
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
                {
                    **{
                        self.entity_config.dimension_fields[i][1]: t[i]
                        for i in range(len(self.entity_config.dimension_fields))
                    },
                    'listen_count': t[len(self.entity_config.dimension_fields)],
                }
                for t in entities_tuples
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
            'type': 'couchdb_data_start',
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
            'type': 'couchdb_data_end',
            'entity_type': entity_type,
            'time_range': time_range,
            'database': database,
        }

    def generate_stats_messages(
        self,
        time_range: str,
        user_results: dict[int, list[dict]],
        database: str,
        batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Generate batched RMQ messages for stats data.

        Stats are batched to reduce RMQ message count while keeping
        individual message sizes manageable.

        Args:
            time_range: The time range for these stats
            user_results: Dict mapping user_id to their stats list
            database: The database name to insert into
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
                    entity_type: stats,
                })

            yield {
                'type': 'clk_user_entity',
                'entity_type': entity_type,
                'time_range': time_range,
                'database': database,
                'data': batch_data,
            }

    def update_cache_batch(
        self,
        time_range: str,
        user_results: dict[int, list[dict]],
    ):
        """Batch update CouchDB cache for multiple users using bulk API with threading."""
        entity_type = self.entity_config.entity_type
        db_name = self.get_couch_db_name(entity_type, time_range)

        docs = []
        for user_id, stats in user_results.items():
            doc = {
                '_id': str(user_id),
                'user_id': user_id,
                'computed_at': datetime.now(tz=timezone.utc).isoformat(),
                'count': len(stats),
                'stats': stats,
            }
            docs.append(doc)

        if not docs:
            return

        self.create_couch_db(db_name)

        num_workers = self.config.couch_workers
        chunk_size = (len(docs) + num_workers - 1) // num_workers
        chunks = [docs[i:i + chunk_size] for i in range(0, len(docs), chunk_size)]

        couch_start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(self._insert_docs, db_name, chunk)
                for chunk in chunks
            ]
            for future in as_completed(futures):
                future.result()

        couch_elapsed = time.perf_counter() - couch_start
        logger.info(f"CouchDB insert took {couch_elapsed:.2f}s for {len(docs)} docs ({num_workers} workers)")

    def _insert_docs(self, db_name: str, docs: list[dict]):
        """Insert documents using CouchDB bulk API with conflict handling."""
        if not docs:
            return

        bulk_url = f"{self.couch_base_url}/{db_name}/_bulk_docs"
        data = orjson.dumps({"docs": docs})

        response = requests.post(
            bulk_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        conflict_doc_ids = []
        for doc_status in response.json():
            if doc_status.get("error") == "conflict":
                conflict_doc_ids.append(doc_status["id"])

        if not conflict_doc_ids:
            return

        bulk_get_url = f"{self.couch_base_url}/{db_name}/_bulk_get"
        conflict_request = orjson.dumps({"docs": [{"id": doc_id} for doc_id in conflict_doc_ids]})

        response = requests.post(
            bulk_get_url,
            data=conflict_request,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        revs_map = {}
        for result in response.json()["results"]:
            existing_doc = result["docs"][0]["ok"]
            revs_map[existing_doc["_id"]] = existing_doc["_rev"]

        docs_to_update = []
        for doc in docs:
            if doc["_id"] in revs_map:
                doc["_rev"] = revs_map[doc["_id"]]
                docs_to_update.append(doc)

        if docs_to_update:
            data = orjson.dumps({"docs": docs_to_update})
            response = requests.post(
                bulk_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

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
    ) -> int:
        """Refresh cache for multiple users for a specific time range."""
        if not user_ids:
            return 0

        user_entities = self.compute_top_entities_batch(time_range, user_ids, self.config.top_n)
        self.update_cache_batch(time_range, user_entities)

        total_entities = sum(len(e) for e in user_entities.values())
        entity_type = self.entity_config.entity_type
        logger.info(f"  {time_range}: {len(user_ids)} users, {total_entities} total {entity_type}s cached")

        return len(user_ids)

    def refresh_time_range_batch_for_rmq(
        self,
        time_range: str,
        user_ids: list[int],
        database: str,
        message_batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Compute stats for multiple users and yield RMQ messages.

        Args:
            time_range: The time range to compute stats for
            user_ids: List of user IDs to process
            database: The database name to include in messages
            message_batch_size: Number of users per RMQ message

        Yields:
            RMQ messages with stats data
        """
        if not user_ids:
            return

        user_entities = self.compute_top_entities_batch(time_range, user_ids, self.config.top_n)

        total_entities = sum(len(e) for e in user_entities.values())
        entity_type = self.entity_config.entity_type
        logger.info(f"  {time_range}: {len(user_ids)} users, {total_entities} total {entity_type}s computed")

        yield from self.generate_stats_messages(time_range, user_entities, database, message_batch_size)

    def run_hourly_job(self, batch_size: int = 1000, deletion_cutoff: Optional[datetime] = None):
        """
        Run the hourly job:
        1. Process pending deletions
        2. For each time_range, find stale users and refresh them
        """
        entity_type = self.entity_config.entity_type
        logger.info(f"Starting hourly job for {entity_type}...")

        deletions = self.process_deletions(cutoff=deletion_cutoff)
        logger.info(f"Processed {deletions} deletions")

        cache_state = self.get_cache_state()

        total_users_refreshed = 0
        for time_range, config in TIME_RANGES.items():
            state = cache_state.get(time_range, {})
            cached_period_start = state.get('period_start')

            period_start, period_end = self.get_period_bounds(time_range)

            if cached_period_start is not None and cached_period_start != period_start:
                logger.info(f"{time_range}: period rollover detected ({cached_period_start} -> {period_start})")
                self.on_period_rollover(time_range, cached_period_start, period_start)
                self.clear_user_cache_state_for_time_range(time_range)

            stale_users = self.get_stale_users(time_range, period_start, period_end)

            if not stale_users:
                logger.info(f"{time_range}: no stale users")
                continue

            logger.info(f"{time_range}: refreshing {len(stale_users)} users")

            max_created = self.get_listen_max_created()

            users_processed = 0
            for i in range(0, len(stale_users), batch_size):
                batch = stale_users[i:i + batch_size]
                try:
                    users_processed += self.refresh_time_range_batch(time_range, batch)
                    self.update_user_cache_state(batch, time_range, max_created)
                except Exception as e:
                    logger.error(f"Error refreshing {time_range} batch {i}: {e}")

            if users_processed > 0:
                self.update_cache_state(time_range, period_start, max_created)

            total_users_refreshed += users_processed

        logger.info(f"Hourly job for {entity_type} completed. Refreshed {total_users_refreshed} user/time_range combinations")

    def run_hourly_job_for_rmq(
        self,
        batch_size: int = 1000,
        deletion_cutoff: Optional[datetime] = None,
        message_batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Run the hourly job and yield RMQ messages instead of writing to CouchDB.

        For each time_range:
        - If period rollover detected: yield start/data/end messages (new database)
        - Otherwise: yield data messages only (append to existing database)

        Message flow for rollover:
        1. couchdb_data_start - create new database
        2. clk_user_entity (batched) - stats data
        3. couchdb_data_end - cleanup old databases

        Yields:
            RMQ messages with stats data
        """
        entity_type = self.entity_config.entity_type
        logger.info(f"Starting hourly job for {entity_type} (RMQ mode)...")

        deletions = self.process_deletions(cutoff=deletion_cutoff)
        logger.info(f"Processed {deletions} deletions")

        cache_state = self.get_cache_state()

        total_users_processed = 0
        total_messages = 0

        for time_range, config in TIME_RANGES.items():
            state = cache_state.get(time_range, {})
            cached_period_start = state.get('period_start')

            period_start, period_end = self.get_period_bounds(time_range)

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
                database = self.get_couch_db_name(entity_type, time_range, with_timestamp=True)
                # Yield start message for new database
                yield self.generate_start_message(time_range, database)
                total_messages += 1
            else:
                # Use base name (incremental update to existing database)
                database = self.get_couch_db_name(entity_type, time_range, with_timestamp=False)

            max_created = self.get_listen_max_created()
            time_range_message_count = 0

            for i in range(0, len(stale_users), batch_size):
                batch = stale_users[i:i + batch_size]
                try:
                    for message in self.refresh_time_range_batch_for_rmq(
                        time_range, batch, database, message_batch_size
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

        logger.info(f"Hourly job for {entity_type} completed. Computed {total_users_processed} user/time_range combinations, {total_messages} messages")

    def run_full_refresh(self, batch_size: int = 1000):
        """Refresh cache for all users using batch processing."""
        entity_type = self.entity_config.entity_type
        stats_table = self.entity_config.stats_table
        logger.info(f"Starting full refresh for {entity_type}...")

        result = self.ch_client.query(f"""
            SELECT DISTINCT user_id FROM {stats_table}
        """)

        all_users = [row[0] for row in result.result_rows]
        logger.info(f"Found {len(all_users)} users to refresh")

        for time_range in TIME_RANGES:
            logger.info(f"Processing {time_range}...")

            period_start, period_end = self.get_period_bounds(time_range)
            max_created = self.get_listen_max_created()

            for i in range(0, len(all_users), batch_size):
                batch = all_users[i:i + batch_size]
                try:
                    self.refresh_time_range_batch(time_range, batch)
                    self.update_user_cache_state(batch, time_range, max_created)
                    logger.info(f"  Progress: {min(i + batch_size, len(all_users))}/{len(all_users)} users")
                except Exception as e:
                    logger.error(f"Error batch refreshing {time_range} batch {i}: {e}")

            self.update_cache_state(time_range, period_start, max_created)

        logger.info(f"Full refresh for {entity_type} completed")

    def run_full_refresh_for_rmq(
        self,
        batch_size: int = 1000,
        message_batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Run full refresh and yield RMQ messages instead of writing to CouchDB.

        Full refresh always creates new databases with timestamps for all time_ranges.

        Message flow for each time_range:
        1. couchdb_data_start - create new database
        2. clk_user_entity (batched) - stats data
        3. couchdb_data_end - cleanup old databases

        Args:
            batch_size: Number of users to process per ClickHouse query batch
            message_batch_size: Number of users per RMQ message

        Yields:
            RMQ messages with stats data
        """
        entity_type = self.entity_config.entity_type
        stats_table = self.entity_config.stats_table
        logger.info(f"Starting full refresh for {entity_type} (RMQ mode)...")

        result = self.ch_client.query(f"""
            SELECT DISTINCT user_id FROM {stats_table}
        """)

        all_users = [row[0] for row in result.result_rows]
        logger.info(f"Found {len(all_users)} users to refresh")

        total_messages = 0

        for time_range in TIME_RANGES:
            logger.info(f"Processing {time_range}...")

            period_start, period_end = self.get_period_bounds(time_range)
            max_created = self.get_listen_max_created()

            # Full refresh always creates new database with timestamp
            database = self.get_couch_db_name(entity_type, time_range, with_timestamp=True)

            # Yield start message for new database
            yield self.generate_start_message(time_range, database)
            total_messages += 1

            # Clear user cache state since we're doing a full refresh
            self.clear_user_cache_state_for_time_range(time_range)

            time_range_message_count = 0
            for i in range(0, len(all_users), batch_size):
                batch = all_users[i:i + batch_size]
                try:
                    for message in self.refresh_time_range_batch_for_rmq(
                        time_range, batch, database, message_batch_size
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

    def cleanup_old_deletions(self, days: int = 7):
        """Clean up processed deletions older than N days."""
        self.ch_client.command(f"""
            ALTER TABLE deleted_listens_log
            DELETE WHERE processed = 1 AND deleted_at < now() - INTERVAL {days} DAY
        """)
        logger.info(f"Cleaned up deletions older than {days} days")


def delete_listen(
    ch_client,
    user_id: int,
    listened_at: datetime,
    recording_msid: str,
    artist_name: str,
    artist_credit_mbids: list[str],
    recording_mbid: Optional[str] = None,
    track_name: Optional[str] = None,
    release_group_mbid: Optional[str] = None,
    release_group_name: Optional[str] = None,
):
    """
    Delete a listen and log it for stats adjustment.

    This should be called by the application when a user deletes a listen.
    Logs the deletion for all entity types (artist, recording, release_group)
    so that stats caches can be properly invalidated.
    """
    if artist_credit_mbids:
        mbids = artist_credit_mbids
    else:
        mbids = ['']

    recording_id = 0
    if recording_mbid:
        recording_id_query = ch_client.query("""
            SELECT recordingId({mbid:String}, {name:String})
        """, parameters={'mbid': recording_mbid, 'name': track_name or ''})
        recording_id = recording_id_query.first_row[0]
    elif track_name:
        recording_id_query = ch_client.query("""
            SELECT recordingId({mbid:String}, {name:String})
        """, parameters={'mbid': '', 'name': track_name})
        recording_id = recording_id_query.first_row[0]

    release_group_id = 0
    if release_group_mbid:
        release_group_id_query = ch_client.query("""
            SELECT releaseGroupId({mbid:String}, {name:String})
        """, parameters={'mbid': release_group_mbid, 'name': release_group_name or ''})
        release_group_id = release_group_id_query.first_row[0]
    elif release_group_name:
        release_group_id_query = ch_client.query("""
            SELECT releaseGroupId({mbid:String}, {name:String})
        """, parameters={'mbid': '', 'name': release_group_name})
        release_group_id = release_group_id_query.first_row[0]

    for mbid in mbids:
        artist_id_query = ch_client.query("""
            SELECT artistId({mbid:String}, {name:String})
        """, parameters={'mbid': mbid, 'name': artist_name})
        artist_id = artist_id_query.first_row[0]

        ch_client.command("""
            INSERT INTO deleted_listens_log
                (user_id, date, listened_at, artist_id, recording_id, release_group_id)
            VALUES
                ({user_id:UInt32}, {date:Date}, {listened_at:DateTime64(3)},
                 {artist_id:UInt64}, {recording_id:UInt64}, {release_group_id:UInt64})
        """, parameters={
            'user_id': user_id,
            'date': listened_at.date(),
            'listened_at': listened_at,
            'artist_id': artist_id,
            'recording_id': recording_id,
            'release_group_id': release_group_id,
        })

    ch_client.command("""
        DELETE FROM listens
        WHERE user_id = {user_id:UInt32}
          AND listened_at = {listened_at:DateTime64(3)}
          AND recording_msid = {recording_msid:String}
    """, parameters={
        'user_id': user_id,
        'listened_at': listened_at,
        'recording_msid': recording_msid,
    })
