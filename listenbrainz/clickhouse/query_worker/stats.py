"""Publish full per-user stats refreshes to generation-specific CouchDB databases."""
from datetime import datetime, timezone

from more_itertools import chunked

from data.model.common_stat import ALLOWED_STATISTICS_RANGE
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import HOURLY_COUNTS
from listenbrainz.clickhouse.query_worker.listens.aggregates import aggregate_snapshot


def refresh_activity(activity, stats_ranges, query_range):
    yield from refresh_stats(activity, stats_ranges, query_range, lambda: aggregate_snapshot(HOURLY_COUNTS))


def refresh_stats(stat, stats_ranges, query_range, snapshot):
    ranges = ALLOWED_STATISTICS_RANGE if stats_ranges is None else stats_ranges
    if not ranges or any(r not in ALLOWED_STATISTICS_RANGE for r in ranges):
        raise ValueError(f"Invalid {stat} ranges: {ranges}")
    as_of = datetime.now(timezone.utc)
    generation = as_of.strftime("%Y%m%d%H%M%S%f")
    with snapshot() as source:
        for stats_range in dict.fromkeys(ranges):
            database = f"clickhouse_{stat}_{stats_range}_{generation}"
            yield {"type": f"clk_{stat}_start", "database": database}
            count = 0
            start, end, rows = query_range(source, stats_range, as_of)
            for batch in chunked(rows, 25):
                count += len(batch)
                yield {"type": f"clk_{stat}", "database": database, "stats_range": stats_range,
                       "from_ts": int(start.timestamp()), "to_ts": int(end.timestamp()), "data": batch}
            yield {"type": f"clk_{stat}_end", "database": database, "user_count": count}
