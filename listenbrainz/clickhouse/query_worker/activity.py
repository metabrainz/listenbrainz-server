"""Publish full activity refreshes from one pinned hourly snapshot."""
from datetime import datetime, timezone

from more_itertools import chunked

from data.model.common_stat import ALLOWED_STATISTICS_RANGE
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import HOURLY_COUNTS
from listenbrainz.clickhouse.query_worker.listens.aggregates import aggregate_snapshot


def refresh_activity(activity, stats_ranges, query_range):
    ranges = ALLOWED_STATISTICS_RANGE if stats_ranges is None else stats_ranges
    if not ranges or any(r not in ALLOWED_STATISTICS_RANGE for r in ranges):
        raise ValueError(f"Invalid {activity} ranges: {ranges}")
    as_of = datetime.now(timezone.utc)
    generation = as_of.strftime("%Y%m%d%H%M%S%f")
    with aggregate_snapshot(HOURLY_COUNTS) as client:
        for stats_range in dict.fromkeys(ranges):
            database = f"clickhouse_{activity}_{stats_range}_{generation}"
            yield {"type": f"clk_{activity}_start", "database": database}
            count = 0
            start, end, rows = query_range(client, stats_range, as_of)
            for batch in chunked(rows, 25):
                count += len(batch)
                yield {"type": f"clk_{activity}", "database": database, "stats_range": stats_range,
                       "from_ts": int(start.timestamp()), "to_ts": int(end.timestamp()), "data": batch}
            yield {"type": f"clk_{activity}_end", "database": database, "user_count": count}
