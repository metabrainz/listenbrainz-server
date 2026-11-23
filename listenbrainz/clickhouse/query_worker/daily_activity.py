"""Full refresh of user daily activity from a reusable UTC hourly aggregate."""
import calendar
from datetime import datetime, time, timedelta, timezone

from more_itertools import chunked

from data.model.common_stat import ALLOWED_STATISTICS_RANGE
from data.stats_range import dates_for_stats_range
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import HOURLY_COUNTS
from listenbrainz.clickhouse.query_worker.listens.aggregates import aggregate_snapshot


def daily_activity_rows(client, start_day, end_day):
    query = """
        SELECT user_id, groupArray((weekday, hour, total))
          FROM (
                SELECT user_id, toDayOfWeek(day) AS weekday, hour,
                       sum(listen_count) AS total
                  FROM stats_snapshot
                 WHERE day >= {start:Date} AND day < {end:Date}
                 GROUP BY user_id, weekday, hour
                HAVING total > 0
          )
      GROUP BY user_id
    """
    parameters = {"start": start_day, "end": end_day}
    with client.query_rows_stream(query, parameters=parameters) as rows:
        for user_id, cells in rows:
            yield {
                "user_id": user_id,
                "data": [
                    {"day": calendar.day_name[weekday - 1], "hour": hour, "listen_count": count}
                    for weekday, hour, count in sorted(cells)
                ],
            }


def daily_activity(stats_ranges=None):
    ranges = ALLOWED_STATISTICS_RANGE if stats_ranges is None else stats_ranges
    if not ranges or any(r not in ALLOWED_STATISTICS_RANGE for r in ranges):
        raise ValueError(f"Invalid daily activity ranges: {ranges}")
    as_of = datetime.now(timezone.utc)
    generation = as_of.strftime("%Y%m%d%H%M%S%f")
    with aggregate_snapshot(HOURLY_COUNTS) as client:
        for stats_range in dict.fromkeys(ranges):
            database = f"clickhouse_daily_activity_{stats_range}_{generation}"
            yield {"type": "clk_daily_activity_start", "database": database}
            count = 0
            start, end = dates_for_stats_range(stats_range, as_of)
            if stats_range == "all_time":
                end = datetime.combine(as_of.date(), time.max, timezone.utc)
            tomorrow = as_of.date() + timedelta(days=1)
            end_day = tomorrow if stats_range == "all_time" else min(end.date(), tomorrow)
            rows = daily_activity_rows(client, start.date(), end_day)
            for batch in chunked(rows, 25):
                count += len(batch)
                yield {"type": "clk_daily_activity", "database": database, "stats_range": stats_range,
                       "from_ts": int(start.timestamp()), "to_ts": int(end.timestamp()), "data": batch}
            yield {"type": "clk_daily_activity_end", "database": database, "user_count": count}
