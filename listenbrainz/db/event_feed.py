import psycopg2
import psycopg2.extras

import listenbrainz.db.event as db_event
from listenbrainz.db.model.event import EventMetadata
from typing import Dict, List, Optional, Tuple

# LEAST and GREATEST skip a missing date, so an event with only one of its dates uses it as both its first and last day
EVENT_FIRST_DAY = """
    LEAST(
        make_date(ec.begin_date_year, COALESCE(ec.begin_date_month, 1), COALESCE(ec.begin_date_day, 1)),
        make_date(ec.end_date_year, COALESCE(ec.end_date_month, 1), COALESCE(ec.end_date_day, 1))
    )
"""
EVENT_LAST_DAY = """
    GREATEST(
        make_date(ec.end_date_year, COALESCE(ec.end_date_month, 1), COALESCE(ec.end_date_day, 1)),
        make_date(ec.begin_date_year, COALESCE(ec.begin_date_month, 1), COALESCE(ec.begin_date_day, 1))
    )
"""

# an event is upcoming while the later of its begin and end dates is today or later, so festivals in progress
# stay in and a missing month or day is read as the earliest it could be, and an event with no date is ignored
UPCOMING_EVENT_CONDITION = f"{EVENT_LAST_DAY} >= CURRENT_DATE"


def get_event_window_condition(days: Optional[int], past: bool, future: bool) -> Tuple[str, list]:
    """
    Build the SQL condition, and its query parameters, for events that overlap a window around today. The window
    reaches days into the past if past is set and days into the future if future is set, like fresh releases. With
    no days, that side of the window is unbounded, so the defaults match UPCOMING_EVENT_CONDITION.

    Arguments:
        days: how many days the window reaches in each direction, or None for no limit
        past: whether the window reaches into the past
        future: whether the window reaches into the future
    """
    conditions = []
    params = []

    if not past:
        conditions.append(f"{EVENT_LAST_DAY} >= CURRENT_DATE")
    elif days is not None:
        conditions.append(f"{EVENT_LAST_DAY} >= CURRENT_DATE - %s")
        params.append(days)

    if not future:
        conditions.append(f"{EVENT_FIRST_DAY} <= CURRENT_DATE")
    elif days is not None:
        conditions.append(f"{EVENT_FIRST_DAY} <= CURRENT_DATE + %s")
        params.append(days)

    # the date expressions are NULL for an event with no date, so this leaves those events out
    if not conditions:
        conditions.append(f"{EVENT_LAST_DAY} IS NOT NULL")

    return " AND ".join(conditions), params


def get_upcoming_events_for_artists(
    ts_conn,
    artist_mbids: List[str],
    limit: int = 25,
    offset: int = 0,
    days: Optional[int] = None,
    past: bool = False,
    future: bool = True,
    cancelled: bool = False,
) -> List[EventMetadata]:
    """
    Fetch events for a given list of artist MBIDs, ordered by date. By default these are the upcoming, non-cancelled
    events. The optional arguments choose any window around today instead (see get_event_window_condition) and can
    include cancelled events, so despite its name this can also return past events.

    Arguments:
        ts_conn: timescale database connection
        artist_mbids: list of artist MBIDs whose events to fetch
        limit: maximum number of events to return
        offset: number of events to skip for pagination
        days: how many days the window reaches in each direction, or None for no limit
        past: whether to include events in the past
        future: whether to include events in the future
        cancelled: whether to include cancelled events
    """

    if not artist_mbids:
        return []

    window, window_params = get_event_window_condition(days, past, future)

    query = """
        SELECT DISTINCT ec.*
          FROM mapping.mb_event_artist_cache eac
          JOIN mapping.mb_event_cache ec
            ON ec.event_id = eac.event_id
         WHERE eac.artist_mbid = ANY(%s::uuid[])
           AND (%s OR ec.cancelled = false)
           AND {window}
      ORDER BY ec.begin_date_year  NULLS LAST
             , ec.begin_date_month NULLS LAST
             , ec.begin_date_day   NULLS LAST
             , ec.event_time       NULLS LAST
             , ec.event_mbid
         LIMIT %s
        OFFSET %s
    """.format(window=window)

    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (artist_mbids, cancelled, *window_params, limit, offset))
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
    days: Optional[int] = None,
    past: bool = False,
    future: bool = True,
    cancelled: bool = False,
) -> Tuple[List[EventMetadata], int]:
    """
    Fetch events across all artists, ordered by date. By default these are the upcoming, non-cancelled events. The
    optional arguments choose any window around today instead (see get_event_window_condition) and can include
    cancelled events, so despite its name this can also return past events.

    Arguments:
        ts_conn: timescale database connection
        limit: maximum number of events to return
        offset: number of events to skip for pagination
        days: how many days the window reaches in each direction, or None for no limit
        past: whether to include events in the past
        future: whether to include events in the future
        cancelled: whether to include cancelled events
    """

    window, window_params = get_event_window_condition(days, past, future)

    count_query = """
        SELECT COUNT(*)
          FROM mapping.mb_event_cache ec
         WHERE (%s OR ec.cancelled = false)
           AND {window}
    """.format(window=window)

    data_query = """
        SELECT *
          FROM mapping.mb_event_cache ec
         WHERE (%s OR ec.cancelled = false)
           AND {window}
      ORDER BY ec.begin_date_year  NULLS LAST
             , ec.begin_date_month NULLS LAST
             , ec.begin_date_day   NULLS LAST
             , ec.event_time       NULLS LAST
             , ec.event_mbid
         LIMIT %s
        OFFSET %s
    """.format(window=window)

    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(count_query, (cancelled, *window_params))
        total_count = curs.fetchone()[0]

        curs.execute(data_query, (cancelled, *window_params, limit, offset))
        events = [EventMetadata(**dict(row)) for row in curs.fetchall()]

    return events, total_count


def get_genres_and_listen_counts_for_artists(ts_conn, artist_mbids: List[str]) -> Dict[str, dict]:
    """
    Fetch the genres of the given artists from mapping.mb_artist_metadata_cache, most tagged first,
    and their sitewide listen counts from popularity.artist. Returns a dict keyed by artist MBID.

    Arguments:
        ts_conn: timescale database connection
        artist_mbids: list of artist MBIDs to fetch genres and listen counts for
    """
    if not artist_mbids:
        return {}

    query = """
        SELECT a.artist_mbid::TEXT
             , amc.tag_data->'artist' AS artist_tags
             , COALESCE(pa.total_listen_count, 0) AS listen_count
          FROM unnest(%s::uuid[]) AS a(artist_mbid)
     LEFT JOIN mapping.mb_artist_metadata_cache amc
            ON amc.artist_mbid = a.artist_mbid
     LEFT JOIN popularity.artist pa
            ON pa.artist_mbid = a.artist_mbid
    """

    result = {}
    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (artist_mbids,))
        for row in curs.fetchall():
            genres = [tag for tag in row["artist_tags"] or [] if tag.get("genre_mbid")]
            result[row["artist_mbid"]] = {
                "genres": [tag["tag"] for tag in sorted(genres, key=lambda t: t["count"], reverse=True)],
                "listen_count": row["listen_count"],
            }
    return result


def add_performers_to_events(ts_conn, events: List[EventMetadata]) -> List[dict]:
    """
    Serialise the events for the API with their performers added, plus the genres and the highest sitewide
    listen count of their main performers. An event with no main performer uses all its performers instead.

    Arguments:
        ts_conn: timescale database connection
        events: the events to serialise
    """
    artists = db_event.get_artists_for_events(ts_conn, [event.event_id for event in events])
    artist_mbids = list({artist["artist_mbid"] for rows in artists.values() for artist in rows})
    artist_metadata = get_genres_and_listen_counts_for_artists(ts_conn, artist_mbids)

    items = []
    for event in events:
        rows = [
            {
                "artist_mbid": row["artist_mbid"],
                "artist_name": row["relationship_data"].get("credited_as") or row["artist_name"],
                "link_type_name": row["link_type_name"],
            }
            for row in artists.get(event.event_id, [])
        ]
        # MB gives artist and event relationships no order of their own, so after the main performers
        # the order is alphabetical. An artist linked to the event more than once is listed once.
        rows.sort(key=lambda p: (p["link_type_name"] != "main performer", (p["artist_name"] or "").lower()))
        performers = []
        for row in rows:
            if not any(p["artist_mbid"] == row["artist_mbid"] for p in performers):
                performers.append(row)
        headliners = [p for p in performers if p["link_type_name"] == "main performer"] or performers

        genres = []
        for performer in headliners:
            for genre in artist_metadata.get(performer["artist_mbid"], {}).get("genres", []):
                if genre not in genres:
                    genres.append(genre)

        item = event.to_api()
        item["performers"] = performers
        item["genres"] = genres
        item["listen_count"] = max(
            (artist_metadata.get(p["artist_mbid"], {}).get("listen_count", 0) for p in headliners), default=0
        )
        items.append(item)
    return items
