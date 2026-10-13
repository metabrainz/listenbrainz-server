#!/usr/bin/env python3
"""
Stats Cache Manager

Shared machinery for computing per-user stats from ClickHouse and emitting them
as RabbitMQ result messages: time ranges, cache state bookkeeping, CouchDB
database naming, message batching and the hourly (incremental) job loop.

Subclasses (see activity_cache_manager) provide the stat-specific parts: how to
find the users whose stats are stale for a time range and how to compute a batch
of users.

Architecture:
    - ClickHouse stores one row per listen (user_id, listened_at, created)
    - stats are computed straight off the listens table
    - cache state tracked to only update affected users/time_ranges
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

import clickhouse_connect

from clickhouse import config
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

# RabbitMQ's default max_message_size is 16 MiB (128 MiB hard cap). Data
# messages are capped by serialized payload size so no single message
# exceeds it. 8 MiB leaves ample headroom for the message envelope and any
# broker-side overhead.
MAX_MESSAGE_BYTES = 8 * 1024 * 1024

# Stats ranges, in the order they are computed.
# "this_*" = current ongoing period, "*" alone = previous complete period.
TIME_RANGES = (
    'all_time',
    'this_week',
    'this_month',
    'this_year',
    'week',
    'month',
    'quarter',
    'half_yearly',
    'year',
)


# last_computed_created marker for a user whose stats must be recomputed for a time
# range even if they have no listens in it any more (their listens were deleted, or
# older listens were back-filled), so the stale document gets overwritten.
FORCE_RECOMPUTE_CREATED = "1970-01-01 00:00:00.000"


def mark_users_for_recompute(ch_client, users_query: str, parameters: dict | None = None) -> None:
    """Force a recompute of every cached (stat type, time range) of the users selected by ``users_query``.

    ``users_query`` returns ``user_id``s. Users without cache state need no marker: the next
    stats job computes them anyway if they have listens in a range.
    """
    ch_client.command(f"""
        INSERT INTO user_stats_cache_state (user_id, stat_type, time_range, last_computed_created)
        SELECT user_id, stat_type, time_range, toDateTime64('{FORCE_RECOMPUTE_CREATED}', 3)
        FROM user_stats_cache_state FINAL
        WHERE user_id IN ({users_query})
    """, parameters=parameters or {})


@dataclass
class CacheConfig:
    """Configuration for cache manager."""
    ch_host: str = 'localhost'
    ch_port: int = 8123
    ch_database: str = 'default'
    ch_username: str = 'default'
    ch_password: str = ''
    couch_db_prefix: str = ''  # optional, e.g. 'clk' to keep the databases apart from spark's


def get_cache_config() -> CacheConfig:
    """Create CacheConfig from ClickHouse config."""
    return CacheConfig(
        ch_host=config.CLICKHOUSE_HOST,
        ch_port=config.CLICKHOUSE_PORT,
        ch_database=config.CLICKHOUSE_DATABASE,
        ch_username=config.CLICKHOUSE_USERNAME,
        ch_password=config.CLICKHOUSE_PASSWORD,
        couch_db_prefix=config.STATS_COUCH_DB_PREFIX,
    )


class StatsCacheManager:
    """Manages ClickHouse stats computation and RabbitMQ result messages for one stat type."""

    def __init__(self, config: CacheConfig, stat_type: str):
        self.config = config
        self.stat_type = stat_type
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

    # ------------------------------------------------------------------
    # Stat-specific hooks
    # ------------------------------------------------------------------

    def get_period_bounds(self, time_range: str) -> tuple:
        """Return the (start, end) dates of the current period of a time range."""
        raise NotImplementedError

    def get_period_timestamps(self, time_range: str, period_start, period_end) -> tuple[int, int]:
        """Return the API from/to timestamps reported for a time range."""
        raise NotImplementedError

    def get_stale_users(self, time_range: str, period_start, period_end) -> list[int]:
        """Return the users whose cached stats for a time range are out of date."""
        raise NotImplementedError

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
        """Compute stats for a batch of users and yield the RMQ messages carrying them."""
        raise NotImplementedError

    def run_bulk_refresh(self, time_ranges: list[str], message_batch_size: int = 100) -> Iterator[dict]:
        """Recompute every user for the given time ranges into new databases."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # CouchDB database naming
    # ------------------------------------------------------------------

    def get_stats_database_name(self, stat_type: str, time_range: str, with_timestamp: bool = False) -> str:
        """
        Generate ClickHouse stats database name for a stat type and time range.

        Args:
            stat_type: The stat type (daily_activity, listening_activity, ...)
            time_range: The time range (all_time, this_week, etc.)
            with_timestamp: If True, append YYYYMMDD timestamp for new database creation

        Returns:
            Database name like 'daily_activity_all_time' or 'daily_activity_all_time_20240115'
        """
        db_name = self.get_stats_database_prefix(stat_type, time_range)

        if with_timestamp:
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
            db_name = f"{db_name}_{timestamp}"

        return db_name

    def get_stats_database_prefix(self, stat_type: str, time_range: str) -> str:
        """Get ClickHouse stats database prefix for finding the current CouchDB database."""
        name = f"{stat_type}_{time_range}"
        if self.config.couch_db_prefix:
            name = f"{self.config.couch_db_prefix}_{name}"
        return name

    # ------------------------------------------------------------------
    # Cache state
    # ------------------------------------------------------------------

    def get_cache_state(self) -> dict[str, dict]:
        """Get current cache state for all time ranges."""
        state_query = """
            SELECT time_range, last_computed, period_start, to_ts
            FROM stats_cache_state FINAL
            WHERE stat_type = {stat_type:String}
        """
        result = self.ch_client.query(state_query, parameters={'stat_type': self.stat_type})
        return {
            row[0]: {'last_computed': row[1], 'period_start': row[2], 'to_ts': row[3]}
            for row in result.result_rows
        }

    def get_listen_max_created(self):
        """Get the maximum created timestamp from listens table, None if it is empty."""
        result = self.ch_client.query("SELECT maxOrNull(created) FROM listens")
        return result.result_rows[0][0]

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

    def update_cache_state(
        self,
        time_range: str,
        period_start,
        last_computed: datetime,
        to_ts: int,
    ):
        """Update the global cache state for a time_range."""
        self.ch_client.command("""
            INSERT INTO stats_cache_state
                (stat_type, time_range, last_computed, period_start, to_ts)
            VALUES
                ({stat_type:String}, {time_range:String}, {last_computed:DateTime64(3)}, {period_start:Date},
                 {to_ts:Int64})
        """, parameters={
            'stat_type': self.stat_type,
            'time_range': time_range,
            'last_computed': last_computed,
            'period_start': period_start,
            'to_ts': to_ts,
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

        rows = [
            (uid, self.stat_type, time_range, max_created)
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
        # Wait for the mutation: the caller reads the cache state right after this, and
        # a not yet applied delete would make it skip the users it still lists.
        self.ch_client.command("""
            ALTER TABLE user_stats_cache_state
            DELETE WHERE stat_type = {stat_type:String} AND time_range = {time_range:String}
        """, parameters={
            'stat_type': self.stat_type,
            'time_range': time_range,
        }, settings={'mutations_sync': 2})
        logger.info(f"Cleared user cache state for {self.stat_type}/{time_range}")

    # ------------------------------------------------------------------
    # Result messages
    # ------------------------------------------------------------------

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
        return {
            'type': 'clk_stats_database_start',
            'entity_type': self.stat_type,
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
        return {
            'type': 'clk_stats_database_end',
            'entity_type': self.stat_type,
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
        max_message_bytes: int = MAX_MESSAGE_BYTES,
    ) -> Iterator[dict]:
        """
        Generate batched RMQ messages for stats data.

        Stats are batched to reduce RMQ message count while keeping
        individual message sizes manageable. A message is flushed when it
        reaches ``batch_size`` users *or* when adding the next user would push
        its serialized payload past ``max_message_bytes``, so no single
        message exceeds RabbitMQ's ``max_message_size``.

        Args:
            time_range: The time range for these stats
            user_results: Dict mapping user_id to their stats list
            from_ts: Start timestamp for this stats range
            to_ts: End timestamp for this stats range
            database: The exact database name to insert into
            database_prefix: Prefix used by LB to select the latest stats database
            batch_size: Maximum number of users per message batch
            max_message_bytes: Approximate maximum serialized size of a message's
                ``data`` payload. A single user larger than this is still sent
                on its own.

        Yields:
            Messages to send via RMQ
        """
        def make_message(batch_data: list[dict]) -> dict:
            message = {
                'type': 'clk_user_entity',
                'entity': self.stat_type,
                'stats_range': time_range,
                'from_ts': from_ts,
                'to_ts': to_ts,
                'data': batch_data,
            }
            if database is not None:
                message['database'] = database
            if database_prefix is not None:
                message['database_prefix'] = database_prefix
            return message

        batch_data: list[dict] = []
        batch_bytes = 0
        for user_id, stats in user_results.items():
            entry = {
                'user_id': user_id,
                'count': len(stats),
                'data': stats,
            }
            # +1 for the list separator; envelope overhead is covered by the
            # headroom between MAX_MESSAGE_BYTES and the broker limit.
            entry_bytes = len(json.dumps(entry)) + 1

            if batch_data and (
                len(batch_data) >= batch_size
                or batch_bytes + entry_bytes > max_message_bytes
            ):
                yield make_message(batch_data)
                batch_data = []
                batch_bytes = 0

            batch_data.append(entry)
            batch_bytes += entry_bytes

        if batch_data:
            yield make_message(batch_data)

    # ------------------------------------------------------------------
    # Hourly (incremental) job
    # ------------------------------------------------------------------

    def run_hourly_job(
        self,
        batch_size: int = 1000,
        message_batch_size: int = 100,
    ) -> Iterator[dict]:
        """
        Run the hourly job and yield RabbitMQ result messages.

        For each time_range:
        - If period rollover detected, or no period has been computed yet: yield
          start/data/end messages (new database)
        - If the period is the same but the range end moved (all_time and the
          listening activity this_* ranges end at the latest listen): every user's
          stats change, including those without new listens, so the range is
          rebuilt for all users by the bulk path into a new database
        - Otherwise: yield data messages only (append to existing database)

        Message flow for rollover:
        1. clk_stats_database_start - create new database
        2. clk_user_entity (batched) - stats data
        3. clk_stats_database_end - cleanup old databases

        Yields:
            RabbitMQ messages with stats data
        """
        stat_type = self.stat_type
        logger.info(f"Starting hourly job for {stat_type}...")

        # Taken once, before any stale user query: listens inserted while the job
        # runs are newer than this and are picked up by the next run.
        max_created = self.get_listen_max_created()
        if max_created is None:
            logger.info(f"No listens, skipping hourly job for {stat_type}")
            return

        cache_state = self.get_cache_state()

        total_users_processed = 0
        total_messages = 0
        moved_ranges = []

        for time_range in TIME_RANGES:
            state = cache_state.get(time_range, {})
            cached_period_start = state.get('period_start')

            period_start, period_end = self.get_period_bounds(time_range)
            from_ts, to_ts = self.get_period_timestamps(time_range, period_start, period_end)

            if cached_period_start == period_start and state.get('to_ts') != to_ts:
                logger.info(f"{time_range}: range end moved ({state.get('to_ts')} -> {to_ts}), rebuilding all users")
                moved_ranges.append(time_range)
                continue

            # A missing period (first run, or the state was reset by a replacing dump
            # load) is treated as a rollover too: the latest existing database may hold
            # an earlier period, so it must not be appended to.
            is_rollover = cached_period_start != period_start
            if is_rollover:
                logger.info(f"{time_range}: period rollover detected ({cached_period_start} -> {period_start})")
                self.on_period_rollover(time_range, cached_period_start, period_start)
                self.clear_user_cache_state_for_time_range(time_range)

            stale_users = self.get_stale_users(time_range, period_start, period_end)
            logger.info(f"{time_range}: computing stats for {len(stale_users)} users")

            # For rollover, create new database with timestamp; otherwise use existing
            if is_rollover:
                database = self.get_stats_database_name(stat_type, time_range, with_timestamp=True)
                database_prefix = None
                # Yield start message for new database
                yield self.generate_start_message(time_range, database)
                total_messages += 1
            else:
                database = None
                database_prefix = self.get_stats_database_prefix(stat_type, time_range)

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
                        total_messages += 1
                    self.update_user_cache_state(batch, time_range, max_created)
                    total_users_processed += len(batch)
                except Exception as e:
                    logger.error(f"Error computing {time_range} batch {i}: {e}")

            # For rollover, yield end message to cleanup old databases. Sent even if
            # nobody has stats for the new period, so the previous period's stats stop
            # being served. Users of a failed batch keep their stale state and are
            # written to the new (latest) database by the next run.
            if is_rollover:
                yield self.generate_end_message(time_range, database)
                total_messages += 1

            self.update_cache_state(time_range, period_start, max_created, to_ts)

        if moved_ranges:
            for message in self.run_bulk_refresh(moved_ranges, message_batch_size=message_batch_size):
                yield message
                total_messages += 1

        logger.info(
            "Hourly job for %s completed. Computed %d user/time_range combinations, %d messages",
            stat_type,
            total_users_processed,
            total_messages,
        )
