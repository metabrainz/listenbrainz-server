"""Database helpers for the user-partitioned listens database."""

import logging
import time
from typing import Optional, Sequence

import psycopg2
import sqlalchemy
from psycopg2.extras import execute_values
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


logger = logging.getLogger(__name__)

engine: Optional[sqlalchemy.engine.Engine] = None


INSERT_LISTENS_QUERY = """
    INSERT INTO listen (listened_at, created, user_id, recording_msid, data)
         VALUES %s
    ON CONFLICT (user_id, listened_at, recording_msid)
      DO NOTHING
"""

DELETE_USER_LISTENS_QUERY = "DELETE FROM listen WHERE user_id = %s AND created <= %s"


def create_test_listens_connect_strings():
    db_name = "listenbrainz_listens_test"
    db_user = "listenbrainz_listens_test"
    return {
        "DB_CONNECT": f"postgresql://{db_user}:listenbrainz_listens@lb_db/{db_name}",
        "DB_CONNECT_ADMIN": "postgresql://postgres:postgres@lb_db/postgres",
        "DB_CONNECT_ADMIN_LB": f"postgresql://postgres:postgres@lb_db/{db_name}",
        "DB_NAME": db_name,
        "DB_USER": db_user,
    }


def _is_configured(connect_str: Optional[str]) -> bool:
    """Return whether a rendered config value points at the listens database."""
    return bool(
        connect_str
        and not connect_str.startswith("SERVICEDOESNOTEXIST")
        and "KEYDOESNOTEXIST" not in connect_str
    )


def init_db_connection(connect_str, poolclass=NullPool, **engine_kwargs):
    """Initialize the connection to the user-partitioned listens database.

    A missing or unrendered connect string leaves `engine` as None. Ingestion and deletion
    require this database and must fail rather than silently skip their writes.
    """
    global engine
    engine = None
    if not _is_configured(connect_str):
        logger.warning("Listens database is not configured; ingestion and deletion requests cannot be processed.")
        return

    while True:
        try:
            engine = create_engine(connect_str, poolclass=poolclass, **engine_kwargs)
            break
        except psycopg2.OperationalError as e:
            print("Couldn't establish connection to listens database: {}".format(str(e)))
            print("Sleeping 2 seconds and trying again...")
            time.sleep(2)


def insert(rows: Sequence[tuple]):
    """Insert incoming listen rows into the partitioned database, ignoring duplicates."""
    if not rows:
        return
    if engine is None:
        raise RuntimeError("Listens database is required for ingestion")

    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            execute_values(
                cursor,
                INSERT_LISTENS_QUERY,
                rows,
                template="(%s::timestamptz, %s::timestamptz, %s::integer, %s::uuid, %s::jsonb)",
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_pending_listens():
    """Delete pending listens and retain every request and its result atomically."""
    if engine is None:
        raise RuntimeError("Listens database is required to process deletions")
    with engine.begin() as connection:
        # Serialize cron runs within this transaction; the lock is released on rollback too.
        if not connection.execute(sqlalchemy.text("SELECT pg_try_advisory_xact_lock(72419302)")).scalar():
            return
        connection.execute(sqlalchemy.text("""
            WITH pending AS MATERIALIZED (
                SELECT id, user_id, listened_at, recording_msid, listen_created
                  FROM listen_delete_metadata
                 WHERE status = 'pending'
                   FOR UPDATE
            ), deleted AS (
                DELETE FROM listen l
                 USING pending p
                 WHERE l.user_id = p.user_id
                   AND l.listened_at = p.listened_at
                   AND l.recording_msid = p.recording_msid
                RETURNING l.user_id, l.listened_at, l.recording_msid, l.created
            )
            UPDATE listen_delete_metadata d
               SET status = CASE WHEN COALESCE(l.created, p.listen_created) IS NULL
                                 THEN 'invalid' ELSE 'complete'
                            END::listen_delete_metadata_status_enum
                 , listen_created = COALESCE(l.created, p.listen_created)
              FROM pending p
              LEFT JOIN deleted l
                ON l.user_id = p.user_id
               AND l.listened_at = p.listened_at
               AND l.recording_msid = p.recording_msid
             WHERE d.id = p.id
        """))


def delete_user(user_id: int, created):
    """Delete a user's listens through the cutoff and record it until dump cleanup."""
    if engine is None:
        raise RuntimeError("Listens database is required to record history deletions")

    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(DELETE_USER_LISTENS_QUERY, (user_id, created))
            cursor.execute(
                "INSERT INTO deleted_user_listen_history (user_id, max_created) VALUES (%s, %s)",
                (user_id, created),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
