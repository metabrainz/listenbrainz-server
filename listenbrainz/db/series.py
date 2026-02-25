from typing import List, Optional, Tuple

import psycopg2
import psycopg2.extras
from flask import current_app


def get_series_metadata(mb_curs, series_mbid: str) -> Optional[dict]:
    """ Fetch name and type for a MusicBrainz series. """
    query = """
        SELECT s.name, s.gid::text AS mbid, st.name AS type
          FROM musicbrainz.series s
          JOIN musicbrainz.series_type st ON s.type = st.id
         WHERE s.gid = %s
    """
    mb_curs.execute(query, (series_mbid,))
    row = mb_curs.fetchone()
    return dict(row) if row else None


def fetch_recordings_from_series(series_mbid: str) -> Tuple[str, List[str]]:
    """Fetch all recording MBIDs belonging to a MusicBrainz series.

    Opens its own connection to the MB mirror so the caller does not need to
    manage database connections.

    Returns:
        A tuple of (series_name, list_of_recording_mbids)

    Raises:
        ValueError: if the series MBID is not found in the MB mirror.
        ValueError: if the series type is not supported.
    """
    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
            mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:

        series_meta = get_series_metadata(mb_curs, series_mbid)
        if not series_meta:
            raise ValueError(f"Series with MBID {series_mbid} not found.")

        series_name = series_meta["name"]
        series_type = series_meta["type"]

        if series_type == "recording":
            query = """
                SELECT r.gid::text
                  FROM musicbrainz.recording r
                  JOIN musicbrainz.recording_series rs ON rs.entity0 = r.id
                 WHERE rs.entity1 = (SELECT id FROM musicbrainz.series WHERE gid = %s)
              ORDER BY rs.position
            """
        elif series_type == "release":
            # All recordings across every release in the series, preserving order.
            query = """
                SELECT rec.gid::text
                  FROM musicbrainz.recording rec
                  JOIN musicbrainz.track t ON t.recording = rec.id
                  JOIN musicbrainz.medium m ON m.id = t.medium
                  JOIN musicbrainz.release rel ON rel.id = m.release
                  JOIN musicbrainz.release_series rs ON rs.entity0 = rel.id
                 WHERE rs.entity1 = (SELECT id FROM musicbrainz.series WHERE gid = %s)
              ORDER BY rs.position, m.position, t.position
            """
        elif series_type == "release_group":
            query = """
                SELECT rec.gid::text
                  FROM musicbrainz.recording rec
                  JOIN musicbrainz.track t ON t.recording = rec.id
                  JOIN musicbrainz.medium m ON m.id = t.medium
                  JOIN musicbrainz.release rel ON rel.id = m.release
                  JOIN musicbrainz.release_group rg ON rg.id = rel.release_group
                  JOIN musicbrainz.release_group_series rgs ON rgs.entity0 = rg.id
                 WHERE rgs.entity1 = (SELECT id FROM musicbrainz.series WHERE gid = %s)
              ORDER BY rgs.position, rel.id, m.position, t.position
            """
        elif series_type == "work":
            query = """
                SELECT r.gid::text
                  FROM musicbrainz.recording r
                  JOIN musicbrainz.l_recording_work lrw ON lrw.entity0 = r.id
                  JOIN musicbrainz.work w ON w.id = lrw.entity1
                  JOIN musicbrainz.work_series ws ON ws.entity0 = w.id
                 WHERE ws.entity1 = (SELECT id FROM musicbrainz.series WHERE gid = %s)
              ORDER BY ws.position
            """
        else:
            raise ValueError(
                f"Series type '{series_type}' is not supported for playlist creation."
            )

        mb_curs.execute(query, (series_mbid,))
        recording_mbids = [row[0] for row in mb_curs.fetchall()]

    return series_name, recording_mbids
