import psycopg2
import psycopg2.extras

from listenbrainz.db.model.event import EventMetadata
from typing import List, Tuple


def get_upcoming_events_for_artists(
    ts_conn,
    artist_mbids: List[str],
    limit: int = 25,
    offset: int = 0,
) -> List[EventMetadata]:
    """
    Fetch upcoming non-cancelled events for a given list of artist MBIDs.

    Arguments:
        ts_conn: timescale database connection
        artist_mbids: list of artist MBIDs whose events to fetch
        limit: maximum number of events to return
        offset: number of events to skip for pagination
    """

    if not artist_mbids:
        return []

    query = """
        SELECT DISTINCT ec.*
          FROM mapping.mb_event_artist_cache eac
          JOIN mapping.mb_event_cache ec
            ON ec.event_id = eac.event_id
         WHERE eac.artist_mbid = ANY(%s::uuid[])
           AND ec.cancelled = false
           AND ec.ended = false
      ORDER BY ec.begin_date_year  NULLS LAST
             , ec.begin_date_month NULLS LAST
             , ec.begin_date_day   NULLS LAST
             , ec.event_time       NULLS LAST
         LIMIT %s
        OFFSET %s
    """

    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (artist_mbids, limit, offset))
        return [EventMetadata(**dict(row)) for row in curs.fetchall()]


def get_upcoming_events_global(
    ts_conn,
    limit: int = 25,
    offset: int = 0,
) -> Tuple[List[EventMetadata], int]:
    """
    Fetch upcoming, non-cancelled events across all artists.

    Arguments:
        ts_conn: timescale database connection
        limit: maximum number of events to return
        offset: number of events to skip for pagination
    """

    count_query = """
        SELECT COUNT(*)
          FROM mapping.mb_event_cache
         WHERE cancelled = false
           AND ended = false
    """

    data_query = """
        SELECT *
          FROM mapping.mb_event_cache
         WHERE cancelled = false
           AND ended = false
      ORDER BY begin_date_year  NULLS LAST
             , begin_date_month NULLS LAST
             , begin_date_day   NULLS LAST
             , event_time       NULLS LAST
         LIMIT %s
        OFFSET %s
    """

    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(count_query)
        total_count = curs.fetchone()[0]

        curs.execute(data_query, (limit, offset))
        events = [EventMetadata(**dict(row)) for row in curs.fetchall()]

    return events, total_count
