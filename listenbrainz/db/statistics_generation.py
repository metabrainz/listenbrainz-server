"""Helpers for tracking successful Spark statistics generation runs."""

import sqlalchemy

from listenbrainz import db


def mark_statistics_generated(db_conn, stats_type: str):
    """Record that Spark successfully generated the given statistics type."""
    db_conn.execute(sqlalchemy.text("""
        INSERT INTO statistics_generation (stats_type, last_updated)
             VALUES (:stats_type, NOW())
        ON CONFLICT (stats_type)
      DO UPDATE SET last_updated = EXCLUDED.last_updated
    """), {
        "stats_type": stats_type
    })
    db_conn.commit()


def get_statistics_generation_timestamps(db_conn, stats_types=None):
    """Return latest generation timestamps as unix epoch seconds, keyed by stats type."""
    filters = []
    params = {}
    if stats_types is not None:
        filters.append("stats_type = ANY(:stats_types)")
        params["stats_types"] = stats_types

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    query = sqlalchemy.text("""
        SELECT stats_type
             , EXTRACT(EPOCH FROM last_updated)::BIGINT AS last_updated
          FROM statistics_generation
          """ + where_clause + """
    """)

    result = db_conn.execute(query, params)
    return {row["stats_type"]: row["last_updated"] for row in result.mappings()}

