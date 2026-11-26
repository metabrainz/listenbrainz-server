"""Per-user top artists from daily materialized listen counts."""
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from itertools import groupby
from operator import itemgetter

from more_itertools import chunked

from data.stats_range import dates_for_stats_range
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import DAILY_ARTIST_COUNTS
from listenbrainz.clickhouse.query_worker.listens.aggregates import aggregate_snapshot
from listenbrainz.clickhouse.query_worker.stats import refresh_stats


@contextmanager
def _artist_snapshot():
    with aggregate_snapshot(DAILY_ARTIST_COUNTS) as client:
        users = client.query("SELECT DISTINCT user_id FROM stats_snapshot ORDER BY user_id").result_rows
        # Signed changes can leave fully deleted days in unmerged parts.
        latest_day = client.query("""
            SELECT maxOrNull(day) FROM (
                SELECT day FROM stats_snapshot GROUP BY day HAVING sum(listen_count) > 0
            )
        """).first_row[0]
        client.command("""
            CREATE TEMPORARY TABLE stats_artist_names ENGINE = Join(ANY, LEFT, artist_id) AS
            SELECT artist_id, toNullable(min(display_name)) AS artist_name, min(artist_mbid) AS mbid
              FROM artist_metadata GROUP BY artist_id
        """)
        try:
            yield client, users, latest_day
        finally:
            client.command("DROP TEMPORARY TABLE stats_artist_names")


def _artist_rows(client, users, start, end):
    query = """
        WITH counts AS (
            SELECT user_id, artist_id, sum(listen_count) AS listens
              FROM stats_snapshot
             WHERE user_id BETWEEN {first:UInt32} AND {last:UInt32}
               AND day >= {start:Date} AND day < {end:Date}
             GROUP BY user_id, artist_id
            HAVING listens > 0
        ), ranked AS (
            SELECT *, rank() OVER (PARTITION BY user_id ORDER BY listens DESC) AS position,
                   count() OVER (PARTITION BY user_id) AS total
              FROM counts
        )
        SELECT user_id, artist_name, nullIf(mbid, '') AS result_mbid, listens, total
          FROM (SELECT * FROM ranked WHERE position <= 1000) AS top_artists
          ANY LEFT JOIN stats_artist_names USING (artist_id)
         ORDER BY user_id, listens DESC, artist_name DESC, result_mbid DESC NULLS LAST
         LIMIT 1000 BY user_id
    """
    for batch in chunked(users, 1000):
        params = {"start": start.date(), "end": end.date(),
                  "first": batch[0][0], "last": batch[-1][0]}
        with client.query_rows_stream(query, parameters=params) as rows:
            for user_id, records in groupby(rows, itemgetter(0)):
                data = []
                invalid = 0
                for _, name, mbid, listens, total in records:
                    if name is None:
                        raise RuntimeError("Missing artist metadata for a ranked artist")
                    if name:
                        data.append({"artist_name": name, "artist_mbid": mbid, "listen_count": listens})
                    else:
                        invalid += 1
                yield {"user_id": user_id, "count": total - invalid, "data": data}


def _artist_range(snapshot, stats_range, as_of):
    client, users, latest_day = snapshot
    reference = datetime.combine(latest_day or as_of.date(), time.min, timezone.utc)
    if stats_range in ("this_week", "this_month", "this_year"):
        reference -= timedelta(days=1)
    start, end = dates_for_stats_range(stats_range, reference)
    if stats_range == "all_time":
        end = reference + timedelta(days=1)
    return start, end, _artist_rows(client, users, start, end)


def artists(stats_ranges=None):
    yield from refresh_stats("artists", stats_ranges, _artist_range, _artist_snapshot)
