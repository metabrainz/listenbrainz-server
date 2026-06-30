import psycopg2
import psycopg2.extras

from listenbrainz.db.model.event import EventMetadata
from listenbrainz.webserver.views.api_tools import MAX_ITEMS_PER_GET
from typing import Dict, List


def get_metadata_for_event(ts_conn, event_mbid_list: List[str]) -> List[EventMetadata]:
    """
    Fetch event metadata rows from mapping.mb_event_cache for the given MBIDs.
    Raises ValueError if the list exceeds MAX_ITEMS_PER_GET.

    Arguments:
        ts_conn: timescale database connection
        event_mbid_list: list of event MBIDs to fetch
    """
    event_mbid_list = tuple(event_mbid_list)
    if len(event_mbid_list) > MAX_ITEMS_PER_GET:
        raise ValueError("Too many event mbids passed in.")

    query = """
        SELECT *
          FROM mapping.mb_event_cache
         WHERE event_mbid IN %s
      ORDER BY event_mbid
    """

    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (event_mbid_list,))
        return [EventMetadata(**dict(row)) for row in curs.fetchall()]


def get_artists_for_events(ts_conn, event_ids: List[int]) -> Dict[int, list]:
    """
    Fetch performer rows from mapping.mb_event_artist_cache for the given event_ids, with
    each artist's name from mapping.mb_artist_metadata_cache (None if the artist is not in it).
    Returns a dict keyed by event_id so the API layer can merge performers into each
    event without a separate round-trip per event.

    Arguments:
        ts_conn: timescale database connection
        event_ids: list of integer event IDs to fetch performers for
    """
    if not event_ids:
        return {}

    query = """
        SELECT eac.event_id
             , eac.artist_mbid::TEXT
             , amc.artist_data->>'name' AS artist_name
             , eac.link_type_name
             , eac.relationship_data
          FROM mapping.mb_event_artist_cache eac
     LEFT JOIN mapping.mb_artist_metadata_cache amc
            ON amc.artist_mbid = eac.artist_mbid
         WHERE eac.event_id IN %s
      ORDER BY eac.event_id
    """

    result = {}
    with ts_conn.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        curs.execute(query, (tuple(event_ids),))
        for row in curs.fetchall():
            eid = row["event_id"]
            result.setdefault(eid, []).append(
                {
                    "artist_mbid": row["artist_mbid"],
                    "artist_name": row["artist_name"],
                    "link_type_name": row["link_type_name"],
                    "relationship_data": row["relationship_data"],
                }
            )
    return result
