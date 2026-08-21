#!/usr/bin/env python3
"""ClickHouse-backed daily and listening activity statistics.

The public payloads intentionally mirror the Spark statistics:

* daily activity contains the non-empty weekday/hour cells. The API expands
  those cells into the complete 7 x 24 heatmap;
* listening activity contains every comparison bucket, including zero-count
  buckets, with the same labels and timestamp boundaries as Spark.

Hourly refreshes query only stale user batches. Bulk full refreshes first build
one compact intermediate so the source tables are scanned once per activity
type instead of once per time range and user batch.
"""

import calendar
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from typing import Hashable, Iterator

from dateutil.relativedelta import MO, relativedelta

from clickhouse.stats.cache_manager import CacheConfig, StatsCacheManager, TIME_RANGES

logger = logging.getLogger(__name__)

LAST_FM_FOUNDING_YEAR = 2002


@dataclass(frozen=True)
class ActivityConfig:
    """Configuration understood by :class:`ActivityStatsCacheManager`.

    ``StatsCacheManager`` uses ``entity_type`` as the cache/database stat type
    and ``stats_table`` to discover users for a full refresh. Activity queries
    themselves use ``listens`` or ``user_recording_stats_daily`` as appropriate.
    """

    entity_type: str
    stats_table: str = "listens"


DAILY_ACTIVITY_CONFIG = ActivityConfig("daily_activity")
LISTENING_ACTIVITY_CONFIG = ActivityConfig("listening_activity")

ACTIVITY_CONFIGS = {
    DAILY_ACTIVITY_CONFIG.entity_type: DAILY_ACTIVITY_CONFIG,
    LISTENING_ACTIVITY_CONFIG.entity_type: LISTENING_ACTIVITY_CONFIG,
}


@dataclass(frozen=True)
class ListeningActivityBucket:
    key: Hashable
    time_range: str
    start: datetime
    end: datetime

    @property
    def from_ts(self) -> int:
        return int(self.start.timestamp())

    @property
    def to_ts(self) -> int:
        return int(self.end.timestamp())

    def as_dict(self, listen_count: int) -> dict:
        return {
            "time_range": self.time_range,
            "from_ts": self.from_ts,
            "to_ts": self.to_ts,
            "listen_count": listen_count,
        }


@dataclass(frozen=True)
class ActivityRange:
    stats_range: str
    start: datetime
    end: datetime
    end_inclusive: bool = False
    buckets: tuple[ListeningActivityBucket, ...] = ()

    @property
    def from_ts(self) -> int:
        return int(self.start.timestamp())

    @property
    def to_ts(self) -> int:
        return int(self.end.timestamp())


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _midnight(value: date) -> datetime:
    return datetime.combine(value, datetime_time.min, tzinfo=timezone.utc)


def _last_quarter_offset(value: date) -> relativedelta:
    if value.month <= 3:
        return relativedelta(years=-1, month=10, day=1)
    if value.month <= 6:
        return relativedelta(month=1, day=1)
    if value.month <= 9:
        return relativedelta(month=4, day=1)
    return relativedelta(month=7, day=1)


def _last_half_year_offset(value: date) -> relativedelta:
    if value.month <= 6:
        return relativedelta(years=-1, month=7, day=1)
    return relativedelta(month=1, day=1)


def _two_quarters_ago_offset(value: date) -> relativedelta:
    if value.month <= 3:
        return relativedelta(years=-1, month=7, day=1)
    if value.month <= 6:
        return relativedelta(years=-1, month=10, day=1)
    if value.month <= 9:
        return relativedelta(month=1, day=1)
    return relativedelta(month=4, day=1)


def _previous_half_year_offset(value: date) -> relativedelta:
    if value.month <= 6:
        return relativedelta(years=-1, month=1, day=1)
    return relativedelta(years=-1, month=7, day=1)


def get_daily_activity_range(stats_range: str, latest_listen: datetime) -> ActivityRange:
    """Return the same listen bounds used by Spark daily activity stats."""

    latest_listen = _utc(latest_listen)
    if stats_range == "all_time":
        return ActivityRange(
            stats_range,
            datetime(LAST_FM_FOUNDING_YEAR, 1, 1, tzinfo=timezone.utc),
            latest_listen,
            end_inclusive=True,
        )

    latest_date = latest_listen.date()
    if stats_range == "this_week":
        start = latest_date + relativedelta(days=-1, weekday=MO(-1))
        end = start + relativedelta(weeks=1)
    elif stats_range == "this_month":
        offset = relativedelta(months=-1) if latest_date.day == 1 else relativedelta(day=1)
        start = latest_date + offset
        end = start + relativedelta(months=1)
    elif stats_range == "this_year":
        if latest_date.day == 1 and latest_date.month == 1:
            start = latest_date + relativedelta(years=-1)
        else:
            start = latest_date + relativedelta(month=1, day=1)
        end = start + relativedelta(years=1)
    elif stats_range == "week":
        start = latest_date + relativedelta(weeks=-1, weekday=MO(-1))
        end = start + relativedelta(weeks=1)
    elif stats_range == "month":
        start = latest_date + relativedelta(months=-1, day=1)
        end = start + relativedelta(months=1)
    elif stats_range == "quarter":
        start = latest_date + _last_quarter_offset(latest_date)
        end = start + relativedelta(months=3)
    elif stats_range == "half_yearly":
        start = latest_date + _last_half_year_offset(latest_date)
        end = start + relativedelta(months=6)
    elif stats_range == "year":
        start = latest_date + relativedelta(years=-1, month=1, day=1)
        end = start + relativedelta(years=1)
    else:
        raise ValueError(f"Unknown stats range: {stats_range}")

    # Spark's generic range filter uses ``<= to_date``. Preserve that boundary
    # behavior for parity, including a listen submitted exactly at midnight at
    # the end of a completed period.
    return ActivityRange(stats_range, _midnight(start), _midnight(end), end_inclusive=True)


def _listening_bucket_spec(stats_range: str) -> tuple[relativedelta, str]:
    if stats_range == "all_time":
        return relativedelta(years=1), "year"
    if stats_range in {"this_week", "week"}:
        return relativedelta(days=1), "weekday"
    if stats_range in {"this_month", "month", "quarter"}:
        return relativedelta(days=1), "day"
    return relativedelta(months=1), "month"


def _bucket_label(start: datetime, label_type: str) -> str:
    if label_type == "year":
        return str(start.year)
    if label_type == "month":
        return f"{calendar.month_name[start.month]} {start.year}"
    day = f"{start.day:02d} {calendar.month_name[start.month]} {start.year}"
    if label_type == "weekday":
        return f"{calendar.day_name[start.weekday()]} {day}"
    return day


def _bucket_key(start: datetime, label_type: str) -> Hashable:
    if label_type == "year":
        return start.year
    if label_type == "month":
        return start.year * 100 + start.month
    return start.date()


def _make_listening_buckets(
    stats_range: str,
    start: datetime,
    end: datetime,
) -> tuple[ListeningActivityBucket, ...]:
    step, label_type = _listening_bucket_spec(stats_range)
    buckets = []
    bucket_start = start
    while bucket_start < end:
        next_start = bucket_start + step
        buckets.append(ListeningActivityBucket(
            key=_bucket_key(bucket_start, label_type),
            time_range=_bucket_label(bucket_start, label_type),
            start=bucket_start,
            # Spark subtracts one microsecond and then converts to whole seconds.
            end=next_start - timedelta(seconds=1),
        ))
        bucket_start = next_start
    return tuple(buckets)


def get_listening_activity_range(stats_range: str, latest_listen: datetime) -> ActivityRange:
    """Return Spark-compatible comparison bounds and display buckets."""

    latest_listen = _utc(latest_listen)
    if stats_range == "all_time":
        start = datetime(LAST_FM_FOUNDING_YEAR, 1, 1, tzinfo=timezone.utc)
        end = latest_listen
        inclusive = True
    else:
        latest_date = latest_listen.date()
        if stats_range.startswith("this"):
            if stats_range == "this_week":
                offset = relativedelta(weeks=-1, days=-1, weekday=MO(-1))
            elif stats_range == "this_month":
                offset = relativedelta(months=-2) if latest_date.day == 1 else relativedelta(months=-1, day=1)
            else:  # this_year
                if latest_date.day == 1 and latest_date.month == 1:
                    offset = relativedelta(years=-2)
                else:
                    offset = relativedelta(years=-1, month=1, day=1)
            start = _midnight(latest_date + offset)
            end = _midnight(latest_date)
        else:
            if stats_range == "week":
                offset = relativedelta(weeks=-2, weekday=MO(-1))
                duration = relativedelta(weeks=2)
            elif stats_range == "month":
                offset = relativedelta(months=-2, day=1)
                duration = relativedelta(months=2)
            elif stats_range == "quarter":
                offset = _two_quarters_ago_offset(latest_date)
                duration = relativedelta(months=6)
            elif stats_range == "half_yearly":
                offset = _previous_half_year_offset(latest_date)
                duration = relativedelta(months=12)
            elif stats_range == "year":
                offset = relativedelta(years=-2, month=1, day=1)
                duration = relativedelta(years=2)
            else:
                raise ValueError(f"Unknown stats range: {stats_range}")
            start = _midnight(latest_date + offset)
            end = start + duration
        inclusive = False

    return ActivityRange(
        stats_range,
        start,
        end,
        end_inclusive=inclusive,
        buckets=_make_listening_buckets(stats_range, start, end),
    )


def _timestamp_predicate(column: str, activity_range: ActivityRange, literal: bool = False) -> str:
    operator = "<=" if activity_range.end_inclusive else "<"
    if literal:
        start = activity_range.from_ts * 1000
        end = activity_range.to_ts * 1000
        return (
            f"{column} >= fromUnixTimestamp64Milli({start}, 'UTC') "
            f"AND {column} {operator} fromUnixTimestamp64Milli({end}, 'UTC')"
        )
    return (
        f"{column} >= fromUnixTimestamp64Milli({{from_ms:Int64}}, 'UTC') "
        f"AND {column} {operator} fromUnixTimestamp64Milli({{to_ms:Int64}}, 'UTC')"
    )


def _date_predicate(column: str, activity_range: ActivityRange, literal: bool = False) -> str:
    operator = "<=" if activity_range.end_inclusive else "<"
    if literal:
        return (
            f"{column} >= toDate('{activity_range.start.date().isoformat()}') "
            f"AND {column} {operator} toDate('{activity_range.end.date().isoformat()}')"
        )
    return f"{column} >= {{from_date:Date}} AND {column} {operator} {{to_date:Date}}"


def _normalise_bucket_key(value, stats_range: str) -> Hashable:
    _, label_type = _listening_bucket_spec(stats_range)
    if label_type in {"year", "month"}:
        return int(value)
    if isinstance(value, datetime):
        return value.date()
    return value


class ActivityStatsCacheManager(StatsCacheManager):
    """Incremental/full batched activity stats manager."""

    def __init__(self, config: CacheConfig, activity_config: ActivityConfig):
        super().__init__(config, activity_config)
        self.activity_config = activity_config
        self._latest_listen: datetime | None = None
        self._activity_ranges: dict[str, ActivityRange] = {}

    def get_latest_listen(self) -> datetime | None:
        if self._latest_listen is None:
            result = self.ch_client.query("SELECT maxOrNull(listened_at) FROM listens")
            value = result.first_row[0]
            if value is not None:
                self._latest_listen = _utc(value)
        return self._latest_listen

    def get_activity_range(self, time_range: str) -> ActivityRange:
        cached = self._activity_ranges.get(time_range)
        if cached is not None:
            return cached

        latest = self.get_latest_listen()
        if latest is None:
            latest = datetime(LAST_FM_FOUNDING_YEAR, 1, 1, tzinfo=timezone.utc)

        if self.activity_config.entity_type == "daily_activity":
            activity_range = get_daily_activity_range(time_range, latest)
        else:
            activity_range = get_listening_activity_range(time_range, latest)
        self._activity_ranges[time_range] = activity_range
        return activity_range

    def get_period_bounds(self, time_range: str) -> tuple[date, date]:
        activity_range = self.get_activity_range(time_range)
        return activity_range.start.date(), activity_range.end.date()

    def get_period_timestamps(self, time_range: str, period_start, period_end) -> tuple[int, int]:
        activity_range = self.get_activity_range(time_range)
        return activity_range.from_ts, activity_range.to_ts

    def get_stale_users(self, time_range: str, period_start, period_end) -> list[int]:
        activity_range = self.get_activity_range(time_range)
        stat_type = self.activity_config.entity_type
        query = f"""
            WITH cached_users AS (
                SELECT user_id, last_computed_created
                FROM user_stats_cache_state FINAL
                WHERE stat_type = {{stat_type:String}}
                  AND time_range = {{time_range:String}}
            )
            SELECT DISTINCT user_id FROM (
                SELECT DISTINCT s.user_id
                FROM listens s
                WHERE {_timestamp_predicate('s.listened_at', activity_range)}
                  AND NOT EXISTS (
                      SELECT 1 FROM cached_users c WHERE c.user_id = s.user_id
                  )

                UNION ALL

                SELECT c.user_id
                FROM cached_users c
                WHERE EXISTS (
                    SELECT 1 FROM listens l
                    WHERE l.user_id = c.user_id
                      AND l.created > c.last_computed_created
                      AND {_timestamp_predicate('l.listened_at', activity_range)}
                )
            )
        """
        started = time.perf_counter()
        result = self.ch_client.query(query, parameters={
            "stat_type": stat_type,
            "time_range": time_range,
            "from_ms": activity_range.from_ts * 1000,
            "to_ms": activity_range.to_ts * 1000,
        })
        logger.info("Stale users query for %s/%s took %.2fs", stat_type, time_range, time.perf_counter() - started)
        return [row[0] for row in result.result_rows]

    def _compute_daily_activity_batch(
        self,
        user_ids: list[int],
        activity_range: ActivityRange,
    ) -> dict[int, list[dict]]:
        query = f"""
            SELECT
                user_id,
                toDayOfWeek(toTimeZone(listened_at, 'UTC')) AS day_of_week,
                toHour(toTimeZone(listened_at, 'UTC')) AS hour,
                count() AS listen_count
            FROM listens
            WHERE user_id IN ({{user_ids:Array(UInt32)}})
              AND {_timestamp_predicate('listened_at', activity_range)}
            GROUP BY user_id, day_of_week, hour
            ORDER BY user_id, day_of_week, hour
        """
        result = self.ch_client.query(query, parameters={
            "user_ids": user_ids,
            "from_ms": activity_range.from_ts * 1000,
            "to_ms": activity_range.to_ts * 1000,
        })
        user_activity: dict[int, list[dict]] = {}
        for user_id, day_of_week, hour, listen_count in result.result_rows:
            user_activity.setdefault(user_id, []).append({
                "day": calendar.day_name[day_of_week - 1],
                "hour": hour,
                "listen_count": listen_count,
            })
        return user_activity

    @staticmethod
    def _listening_activity_from_counts(
        stats_range: str,
        activity_range: ActivityRange,
        counts: dict[Hashable, int],
    ) -> list[dict]:
        normalised = {
            _normalise_bucket_key(key, stats_range): listen_count
            for key, listen_count in counts.items()
        }
        return [bucket.as_dict(normalised.get(bucket.key, 0)) for bucket in activity_range.buckets]

    def _listening_bucket_expression(self, stats_range: str, column: str = "date") -> str:
        _, label_type = _listening_bucket_spec(stats_range)
        if label_type == "year":
            return f"toYear({column})"
        if label_type == "month":
            return f"toYYYYMM({column})"
        return column

    def _compute_listening_activity_batch(
        self,
        user_ids: list[int],
        activity_range: ActivityRange,
    ) -> dict[int, list[dict]]:
        bucket_expression = self._listening_bucket_expression(activity_range.stats_range)
        query = f"""
            SELECT
                user_id,
                {bucket_expression} AS bucket_key,
                sum(listen_count) AS listen_count
            FROM user_recording_stats_daily
            WHERE user_id IN ({{user_ids:Array(UInt32)}})
              AND {_date_predicate('date', activity_range)}
            GROUP BY user_id, bucket_key
            HAVING listen_count > 0
            ORDER BY user_id, bucket_key
        """
        result = self.ch_client.query(query, parameters={
            "user_ids": user_ids,
            "from_date": activity_range.start.date(),
            "to_date": activity_range.end.date(),
        })
        counts_by_user: dict[int, dict[Hashable, int]] = {}
        for user_id, bucket_key, listen_count in result.result_rows:
            counts_by_user.setdefault(user_id, {})[bucket_key] = listen_count
        return {
            user_id: self._listening_activity_from_counts(
                activity_range.stats_range, activity_range, counts,
            )
            for user_id, counts in counts_by_user.items()
        }

    def compute_activity_batch(
        self,
        time_range: str,
        user_ids: list[int],
    ) -> dict[int, list[dict]]:
        if not user_ids:
            return {}
        activity_range = self.get_activity_range(time_range)
        started = time.perf_counter()
        if self.activity_config.entity_type == "daily_activity":
            result = self._compute_daily_activity_batch(user_ids, activity_range)
        else:
            result = self._compute_listening_activity_batch(user_ids, activity_range)
        logger.info(
            "ClickHouse %s query took %.2fs for %d users",
            self.activity_config.entity_type, time.perf_counter() - started, len(user_ids),
        )
        return result

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
        user_activity = self.compute_activity_batch(time_range, user_ids)
        logger.info(
            "  %s: %d/%d users have %s data",
            time_range, len(user_activity), len(user_ids), self.activity_config.entity_type,
        )
        yield from self.generate_stats_messages(
            time_range,
            user_activity,
            from_ts,
            to_ts,
            database=database,
            database_prefix=database_prefix,
            batch_size=message_batch_size,
        )


class BulkActivityStatsCacheManager(ActivityStatsCacheManager):
    """Single-source-scan full refresh for one activity stat type."""

    INTERMEDIATE_PREFIX = "tmp_bulk_user_"

    @property
    def intermediate_table_name(self) -> str:
        return f"{self.INTERMEDIATE_PREFIX}{self.activity_config.entity_type}_counts"

    def drop_intermediate_table(self) -> None:
        self.ch_client.command(
            f"DROP TABLE IF EXISTS {self.intermediate_table_name} "
            "SETTINGS max_table_size_to_drop = 0"
        )

    def build_intermediate_table(self) -> None:
        if self.activity_config.entity_type == "daily_activity":
            count_columns = ",\n                ".join(
                f"countIf({_timestamp_predicate('listened_at', self.get_activity_range(time_range), literal=True)}) "
                f"AS count_{time_range}"
                for time_range in TIME_RANGES
            )
            all_time = self.get_activity_range("all_time")
            query = f"""
                CREATE TABLE {self.intermediate_table_name}
                ENGINE = MergeTree()
                ORDER BY (user_id, day_of_week, hour)
                AS SELECT
                    user_id,
                    toDayOfWeek(toTimeZone(listened_at, 'UTC')) AS day_of_week,
                    toHour(toTimeZone(listened_at, 'UTC')) AS hour,
                    {count_columns}
                FROM listens
                WHERE {_timestamp_predicate('listened_at', all_time, literal=True)}
                GROUP BY user_id, day_of_week, hour
            """
        else:
            all_time = self.get_activity_range("all_time")
            query = f"""
                CREATE TABLE {self.intermediate_table_name}
                ENGINE = MergeTree()
                ORDER BY (user_id, date)
                AS SELECT
                    user_id,
                    date,
                    sum(listen_count) AS listen_count
                FROM user_recording_stats_daily
                WHERE {_date_predicate('date', all_time, literal=True)}
                GROUP BY user_id, date
                HAVING listen_count > 0
            """
        self.ch_client.command(query)

    def intermediate_row_count(self) -> int:
        result = self.ch_client.query(f"SELECT count() FROM {self.intermediate_table_name}")
        return result.first_row[0]

    def _stream_daily_activity(self, time_range: str):
        count_column = f"count_{time_range}"
        query = f"""
            SELECT
                user_id,
                groupArray(tuple(day_of_week, hour, toInt64({count_column}))) AS activity
            FROM {self.intermediate_table_name}
            WHERE {count_column} > 0
            GROUP BY user_id
            ORDER BY user_id
        """
        with self.ch_client.query_row_block_stream(query) as stream:
            for block in stream:
                for user_id, activity in block:
                    yield user_id, [
                        {
                            "day": calendar.day_name[day_of_week - 1],
                            "hour": hour,
                            "listen_count": listen_count,
                        }
                        for day_of_week, hour, listen_count in sorted(activity)
                    ]

    def _stream_listening_activity(self, time_range: str):
        activity_range = self.get_activity_range(time_range)
        bucket_expression = self._listening_bucket_expression(time_range)
        query = f"""
            WITH bucket_counts AS (
                SELECT
                    user_id,
                    {bucket_expression} AS bucket_key,
                    sum(listen_count) AS listen_count
                FROM {self.intermediate_table_name}
                WHERE {_date_predicate('date', activity_range, literal=True)}
                GROUP BY user_id, bucket_key
                HAVING listen_count > 0
            )
            SELECT
                user_id,
                groupArray(tuple(bucket_key, listen_count)) AS activity
            FROM bucket_counts
            GROUP BY user_id
            ORDER BY user_id
        """
        with self.ch_client.query_row_block_stream(query) as stream:
            for block in stream:
                for user_id, activity in block:
                    yield user_id, self._listening_activity_from_counts(
                        time_range,
                        activity_range,
                        dict(activity),
                    )

    def stream_activity_for_range(self, time_range: str):
        if self.activity_config.entity_type == "daily_activity":
            return self._stream_daily_activity(time_range)
        return self._stream_listening_activity(time_range)

    def _flush_user_batch(
        self,
        time_range: str,
        user_batch: dict[int, list[dict]],
        database: str,
        message_batch_size: int,
        max_created,
    ) -> Iterator[dict]:
        if not user_batch:
            return
        activity_range = self.get_activity_range(time_range)
        yield from self.generate_stats_messages(
            time_range,
            user_batch,
            activity_range.from_ts,
            activity_range.to_ts,
            database=database,
            batch_size=message_batch_size,
        )
        self.update_user_cache_state(list(user_batch), time_range, max_created)

    def _accumulate_and_flush(
        self,
        rows,
        time_range: str,
        database: str,
        message_batch_size: int,
        user_flush_size: int,
        max_created,
    ) -> Iterator[dict]:
        user_batch: dict[int, list[dict]] = {}
        for user_id, activity in rows:
            user_batch[user_id] = activity
            if len(user_batch) >= user_flush_size:
                yield from self._flush_user_batch(
                    time_range, user_batch, database, message_batch_size, max_created,
                )
                user_batch = {}
        yield from self._flush_user_batch(
            time_range, user_batch, database, message_batch_size, max_created,
        )

    def run_full_refresh(
        self,
        message_batch_size: int = 100,
        user_flush_size: int = 5000,
    ) -> Iterator[dict]:
        stat_type = self.activity_config.entity_type
        logger.info("Starting bulk full refresh for %s...", stat_type)

        if self.get_latest_listen() is None:
            logger.info("No listens found for %s full refresh", stat_type)
            return

        self.drop_intermediate_table()
        try:
            started = time.perf_counter()
            self.build_intermediate_table()
            row_count = self.intermediate_row_count()
            logger.info(
                "Built intermediate %s (%d rows) in %.1fs",
                self.intermediate_table_name, row_count, time.perf_counter() - started,
            )
            if row_count == 0:
                return

            max_created = self.get_listen_max_created()
            total_messages = 0
            for time_range in TIME_RANGES:
                activity_range = self.get_activity_range(time_range)
                database = self.get_stats_database_name(stat_type, time_range, with_timestamp=True)
                yield self.generate_start_message(time_range, database)
                total_messages += 1
                self.clear_user_cache_state_for_time_range(time_range)

                data_messages = 0
                range_started = time.perf_counter()
                rows = self.stream_activity_for_range(time_range)
                for message in self._accumulate_and_flush(
                    rows,
                    time_range,
                    database,
                    message_batch_size,
                    user_flush_size,
                    max_created,
                ):
                    yield message
                    data_messages += 1
                    total_messages += 1

                logger.info(
                    "  %s: %d data messages in %.1fs",
                    time_range, data_messages, time.perf_counter() - range_started,
                )
                if data_messages:
                    yield self.generate_end_message(time_range, database)
                    total_messages += 1
                self.update_cache_state(time_range, activity_range.start.date(), max_created)

            logger.info(
                "Bulk refresh for %s completed. %d messages generated",
                stat_type, total_messages,
            )
        finally:
            self.drop_intermediate_table()
