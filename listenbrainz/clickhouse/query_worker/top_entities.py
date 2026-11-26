"""Rank per-user entities across calendar ranges using daily signed counts."""
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from itertools import groupby
from operator import itemgetter

from more_itertools import chunked

from data.stats_range import dates_for_stats_range
from listenbrainz.clickhouse.query_worker.listens.aggregates import aggregate_snapshot
from listenbrainz.clickhouse.query_worker.stats import refresh_stats


@contextmanager
def temporary_table(client, name, definition, parameters=None):
    client.command(f"CREATE TEMPORARY TABLE {name} {definition}", parameters=parameters)
    try:
        yield
    finally:
        client.command(f"DROP TEMPORARY TABLE {name} SETTINGS max_table_size_to_drop = 0")


def refresh_top_entities(stat, stats_ranges, counts, metadata, rows, day_table="stats_snapshot"):
    @contextmanager
    def snapshot():
        with aggregate_snapshot(counts) as client:
            users = client.query("SELECT DISTINCT user_id FROM stats_snapshot ORDER BY user_id").result_rows
            # Signed changes can leave fully deleted days in unmerged parts.
            latest_day = client.query(f"""
                SELECT maxOrNull(day) FROM (
                    SELECT day FROM {day_table} GROUP BY day HAVING sum(listen_count) > 0
                )
            """).first_row[0]
            with metadata(client):
                yield client, users, latest_day

    def query_range(source, stats_range, as_of):
        client, users, latest_day = source
        reference = datetime.combine(latest_day or as_of.date(), time.min, timezone.utc)
        if stats_range in ("this_week", "this_month", "this_year"):
            reference -= timedelta(days=1)
        start, end = dates_for_stats_range(stats_range, reference)
        if stats_range == "all_time":
            end = reference + timedelta(days=1)
        return start, end, rows(client, users, start, end)

    yield from refresh_stats(stat, stats_ranges, query_range, snapshot)


def ranked_entities(client, users, start, end, entity_id, fields, tie_breakers):
    query = f"""
        WITH counts AS (
            SELECT user_id, {entity_id}, sum(listen_count) AS listens
              FROM stats_snapshot
             WHERE user_id BETWEEN {{first:UInt32}} AND {{last:UInt32}}
               AND day >= {{start:Date}} AND day < {{end:Date}}
             GROUP BY user_id, {entity_id}
            HAVING listens > 0
        ), ranked AS (
            SELECT *, rank() OVER (PARTITION BY user_id ORDER BY listens DESC) AS position,
                   count() OVER (PARTITION BY user_id) AS total
              FROM counts
        )
        SELECT user_id, listens, total, {fields}
          FROM (SELECT * FROM ranked WHERE position <= 1000) AS top_entities
          ANY LEFT JOIN stats_labels USING ({entity_id})
         ORDER BY user_id, listens DESC, {tie_breakers}
         LIMIT 1000 BY user_id
    """
    for batch in chunked(users, 1000):
        params = {"start": start.date(), "end": end.date(),
                  "first": batch[0][0], "last": batch[-1][0]}
        with client.query_rows_stream(query, parameters=params, query_formats={"UUID": "string"}) as rows:
            yield from groupby(rows, itemgetter(0))
