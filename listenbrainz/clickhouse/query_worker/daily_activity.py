"""Full refresh of user daily activity from a reusable UTC hourly aggregate."""
import calendar
from datetime import datetime, time, timedelta, timezone

from data.stats_range import dates_for_stats_range
from listenbrainz.clickhouse.query_worker.activity import refresh_activity


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


def _daily_activity_range(client, stats_range, as_of):
    start, end = dates_for_stats_range(stats_range, as_of)
    if stats_range == "all_time":
        end = datetime.combine(as_of.date(), time.max, timezone.utc)
    tomorrow = as_of.date() + timedelta(days=1)
    end_day = tomorrow if stats_range == "all_time" else min(end.date(), tomorrow)
    return start, end, daily_activity_rows(client, start.date(), end_day)


def daily_activity(stats_ranges=None):
    yield from refresh_activity("daily_activity", stats_ranges, _daily_activity_range)
