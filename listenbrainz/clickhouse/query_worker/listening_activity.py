"""User listen counts in calendar buckets across comparable periods."""
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from data.stats_range import dates_for_stats_range
from listenbrainz.clickhouse.query_worker.stats import refresh_activity


def _listening_activity_rows(client, start, end_day, step, label, bucket):
    # Build the calendar once so every active user gets the same ordered buckets.
    calendar = {}
    cursor = start
    while cursor.date() < end_day:
        next_cursor = cursor + step
        calendar[cursor.date()] = {
            "time_range": cursor.strftime(label),
            "from_ts": int(cursor.timestamp()),
            "to_ts": int(next_cursor.timestamp()) - 1,
        }
        cursor = next_cursor

    query = f"""
        SELECT user_id, groupArray((period, total))
          FROM (
                SELECT user_id, {bucket} AS period, sum(listen_count) AS total
                  FROM stats_snapshot
                 WHERE day >= {{start:Date}} AND day < {{end:Date}}
                 GROUP BY user_id, period
                HAVING total > 0
          )
         GROUP BY user_id
    """
    with client.query_rows_stream(query, parameters={"start": start.date(), "end": end_day}) as rows:
        for user_id, cells in rows:
            counts = dict(cells)
            yield {"user_id": user_id, "data": [
                {**record, "listen_count": counts.get(day, 0)} for day, record in calendar.items()
            ]}


def _listening_activity_range(client, stats_range, as_of):
    if stats_range == "all_time":
        start, _ = dates_for_stats_range(stats_range, as_of)
        end = as_of.replace(hour=23, minute=59, second=59, microsecond=0)
        end_day = end.date() + timedelta(days=1)
        step, label, bucket = relativedelta(years=1), "%Y", "toStartOfYear(day)"
    else:
        period = stats_range.removeprefix("this_")
        if stats_range.startswith("this_"):
            # Compare through yesterday, including on the first day of a new period.
            end = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
            start, _ = dates_for_stats_range(period, end - timedelta(days=1))
        else:
            previous, end = dates_for_stats_range(period, as_of)
            start, _ = dates_for_stats_range(period, previous)
        end_day = end.date()
        if period in ("year", "half_yearly"):
            step, label, bucket = relativedelta(months=1), "%B %Y", "toStartOfMonth(day)"
        else:
            step, bucket = timedelta(days=1), "day"
            label = "%A %d %B %Y" if period == "week" else "%d %B %Y"

    return start, end, _listening_activity_rows(client, start, end_day, step, label, bucket)


def listening_activity(stats_ranges=None):
    yield from refresh_activity("listening_activity", stats_ranges, _listening_activity_range)
