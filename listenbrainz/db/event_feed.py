import psycopg2
import psycopg2.extras

from listenbrainz.db.model.event import EventMetadata
from typing import List, Tuple

# an event is upcoming while the later of its begin and end dates is today or later, so festivals in progress
# stay in and a missing month or day is read as the earliest it could be, and an event with no date is ignored
UPCOMING_EVENT_CONDITION = """
    GREATEST(
        make_date(ec.end_date_year, COALESCE(ec.end_date_month, 1), COALESCE(ec.end_date_day, 1)),
        make_date(ec.begin_date_year, COALESCE(ec.begin_date_month, 1), COALESCE(ec.begin_date_day, 1))
    ) >= CURRENT_DATE
"""


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
           AND {upcoming}
      ORDER BY ec.begin_date_year  NULLS LAST
             , ec.begin_date_month NULLS LAST
             , ec.begin_date_day   NULLS LAST
             , ec.event_time       NULLS LAST
         LIMIT %s
        OFFSET %s
    """.format(upcoming=UPCOMING_EVENT_CONDITION)

    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (artist_mbids, limit, offset))
        return [EventMetadata(**dict(row)) for row in curs.fetchall()]


def get_past_events_for_artists(
    ts_conn,
    artist_mbids: List[str],
    limit: int = 25,
    offset: int = 0,
) -> List[EventMetadata]:
    """
    Fetch past non-cancelled events for a given list of artist MBIDs, most recent first.

    Arguments:
        ts_conn: timescale database connection
        artist_mbids: list of artist MBIDs whose events to fetch
        limit: maximum number of events to return
        offset: number of events to skip for pagination
    """

    if not artist_mbids:
        return []

    # the upcoming condition is NULL for an event with no date, so NOT leaves those events out here too
    query = """
        SELECT DISTINCT ec.*
          FROM mapping.mb_event_artist_cache eac
          JOIN mapping.mb_event_cache ec
            ON ec.event_id = eac.event_id
         WHERE eac.artist_mbid = ANY(%s::uuid[])
           AND ec.cancelled = false
           AND NOT ({upcoming})
      ORDER BY ec.begin_date_year  DESC NULLS LAST
             , ec.begin_date_month DESC NULLS LAST
             , ec.begin_date_day   DESC NULLS LAST
             , ec.event_time       DESC NULLS LAST
         LIMIT %s
        OFFSET %s
    """.format(upcoming=UPCOMING_EVENT_CONDITION)

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
          FROM mapping.mb_event_cache ec
         WHERE ec.cancelled = false
           AND {upcoming}
    """.format(upcoming=UPCOMING_EVENT_CONDITION)

    data_query = """
        SELECT *
          FROM mapping.mb_event_cache ec
         WHERE ec.cancelled = false
           AND {upcoming}
      ORDER BY ec.begin_date_year  NULLS LAST
             , ec.begin_date_month NULLS LAST
             , ec.begin_date_day   NULLS LAST
             , ec.event_time       NULLS LAST
         LIMIT %s
        OFFSET %s
    """.format(upcoming=UPCOMING_EVENT_CONDITION)

    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(count_query)
        total_count = curs.fetchone()[0]

        curs.execute(data_query, (limit, offset))
        events = [EventMetadata(**dict(row)) for row in curs.fetchall()]

    return events, total_count
