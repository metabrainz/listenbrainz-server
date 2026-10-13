"""Shared machinery for per-user stats: cache state, CouchDB database names, result
messages and the hourly job. Subclasses (see activity_cache_manager) find the stale
users of a time range and compute their stats.
"""

import logging
from datetime import datetime, timezone
from itertools import batched
from typing import Iterator

from clickhouse.client import ClickHouseConnection
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

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


# last_computed_created marking a user to recompute even with no listens left in a
# range (deleted or back-filled listens), so their old stats get overwritten.
FORCE_RECOMPUTE_CREATED = "1970-01-01 00:00:00.000"


def mark_users_for_recompute(ch_client, users_query: str, parameters: dict | None = None) -> None:
    """Force a recompute of every cached stat of the users ``users_query`` selects."""
    ch_client.command(f"""
        INSERT INTO user_stats_cache_state (user_id, stat_type, time_range, last_computed_created)
        SELECT user_id, stat_type, time_range, toDateTime64('{FORCE_RECOMPUTE_CREATED}', 3)
        FROM user_stats_cache_state FINAL
        WHERE user_id IN ({users_query})
    """, parameters=parameters or {})


class StatsCacheManager:
    """Manages ClickHouse stats computation and RabbitMQ result messages for one stat type."""

    def __init__(self, connection: ClickHouseConnection, stat_type: str):
        self.connection = connection
        self.stat_type = stat_type
        self.ch_client = None

    def connect(self):
        """Establish a connection to ClickHouse."""
        self.ch_client = self.connection.connect(form_encode_query_params=True)
        logger.info("Connected to ClickHouse at %s:%s", self.connection.host, self.connection.port)
        ensure_stats_schema(self.ch_client)

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

    def get_stats_database_name(self, stat_type: str, time_range: str) -> str:
        """Name of a new stats database for a stat type and time range, e.g. 'daily_activity_all_time_20240115'."""
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        return f"{self.get_stats_database_prefix(stat_type, time_range)}_{timestamp}"

    def get_stats_database_prefix(self, stat_type: str, time_range: str) -> str:
        """Database name without the date: the Spark name, as the stats live in their own CouchDB."""
        return f"{stat_type}_{time_range}"

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
        """Hook called when the period of a time range rolls over."""
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
        # Wait for the delete: the caller reads the cache state right after.
        self.ch_client.command("""
            ALTER TABLE user_stats_cache_state
            DELETE WHERE stat_type = {stat_type:String} AND time_range = {time_range:String}
        """, parameters={
            'stat_type': self.stat_type,
            'time_range': time_range,
        }, settings={'mutations_sync': 2})
        logger.info(f"Cleared user cache state for {self.stat_type}/{time_range}")

    def _database_message(self, message_type: str, time_range: str, database: str) -> dict:
        return {
            'type': message_type,
            'entity_type': self.stat_type,
            'time_range': time_range,
            'database': database,
        }

    def generate_start_message(self, time_range: str, database: str) -> dict:
        """Message asking the LB handler to create a new stats database."""
        return self._database_message('clk_stats_database_start', time_range, database)

    def generate_end_message(self, time_range: str, database: str) -> dict:
        """Message asking the LB handler to drop the older databases of this stat / time range."""
        return self._database_message('clk_stats_database_end', time_range, database)

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
        """Yield messages with the stats of up to ``batch_size`` users each.

        ``database`` names the database to write to; ``database_prefix`` instead makes LB use
        the latest database with that prefix. Oversized messages are split when published
        (request_consumer.serialize_result).
        """
        for batch in batched(user_results.items(), batch_size):
            message = {
                'type': 'clk_user_entity',
                'entity': self.stat_type,
                'stats_range': time_range,
                'from_ts': from_ts,
                'to_ts': to_ts,
                'data': [{'user_id': user_id, 'count': len(stats), 'data': stats} for user_id, stats in batch],
            }
            if database is not None:
                message['database'] = database
            if database_prefix is not None:
                message['database_prefix'] = database_prefix
            yield message

    def run_hourly_job(
        self,
        batch_size: int = 1000,
        message_batch_size: int = 100,
    ) -> Iterator[dict]:
        """Yield result messages for the users whose stats changed, per time range.

        On a period rollover a range goes to a new database: start message, data, end
        message. The bulk refresh rebuilds a range that was never computed (first run, or
        reset by a full dump load) and one whose end moved (ranges ending at the latest
        listen), as every user's stats change. Otherwise the changed users are appended to
        the current database.
        """
        stat_type = self.stat_type
        logger.info(f"Starting hourly job for {stat_type}...")

        # Taken before the stale user queries; listens inserted later go to the next run.
        max_created = self.get_listen_max_created()
        if max_created is None:
            logger.info(f"No listens, skipping hourly job for {stat_type}")
            return

        cache_state = self.get_cache_state()

        total_users_processed = 0
        total_messages = 0
        bulk_ranges = []

        for time_range in TIME_RANGES:
            state = cache_state.get(time_range, {})
            cached_period_start = state.get('period_start')

            period_start, period_end = self.get_period_bounds(time_range)
            from_ts, to_ts = self.get_period_timestamps(time_range, period_start, period_end)

            if cached_period_start is None:
                logger.info(f"{time_range}: not computed yet, rebuilding all users")
                bulk_ranges.append(time_range)
                continue
            if cached_period_start == period_start and state.get('to_ts') != to_ts:
                logger.info(f"{time_range}: range end moved ({state.get('to_ts')} -> {to_ts}), rebuilding all users")
                bulk_ranges.append(time_range)
                continue

            is_rollover = cached_period_start != period_start
            if is_rollover:
                logger.info(f"{time_range}: period rollover detected ({cached_period_start} -> {period_start})")
                self.on_period_rollover(time_range, cached_period_start, period_start)
                self.clear_user_cache_state_for_time_range(time_range)

            stale_users = self.get_stale_users(time_range, period_start, period_end)
            logger.info(f"{time_range}: computing stats for {len(stale_users)} users")

            if is_rollover:
                database = self.get_stats_database_name(stat_type, time_range)
                database_prefix = None
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
                except Exception:
                    logger.error("Error computing %s batch %d", time_range, i, exc_info=True)

            # Sent even without data, so the previous period stops being served.
            if is_rollover:
                yield self.generate_end_message(time_range, database)
                total_messages += 1

            self.update_cache_state(time_range, period_start, max_created, to_ts)

        if bulk_ranges:
            for message in self.run_bulk_refresh(bulk_ranges, message_batch_size=message_batch_size):
                yield message
                total_messages += 1

        logger.info(
            "Hourly job for %s completed. Computed %d user/time_range combinations, %d messages",
            stat_type,
            total_users_processed,
            total_messages,
        )
