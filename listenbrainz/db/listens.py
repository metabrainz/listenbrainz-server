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
      DO UPDATE
            SET created = excluded.created
              , data = excluded.data
          WHERE excluded.created > listen.created
"""

DELETE_LISTENS_QUERY = """
    DELETE FROM listen l
     USING (VALUES %s) AS deleted (user_id, listened_at, recording_msid)
     WHERE l.user_id = deleted.user_id
       AND l.listened_at = deleted.listened_at
       AND l.recording_msid = deleted.recording_msid
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

    A missing or unrendered connect string leaves `engine` as None, which makes every write here
    a no-op. Warn, since in a deployment that silently stops the dual write.
    """
    global engine
    engine = None
    if not _is_configured(connect_str):
        logger.warning("Listens database is not configured, listens will NOT be mirrored to the"
                       " partitioned database.")
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
    """Idempotently mirror Timescale listen rows into the partitioned database."""
    if not rows or engine is None:
        return

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


def delete(deletes: Sequence[tuple]):
    """Delete logical listens from the partitioned database."""
    if not deletes or engine is None:
        return

    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            execute_values(
                cursor,
                DELETE_LISTENS_QUERY,
                deletes,
                template="(%s::integer, %s::timestamptz, %s::uuid)",
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_user(user_id: int, created):
    """Delete a user's listens up to the same cutoff used by Timescale."""
    if engine is None:
        return

    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(DELETE_USER_LISTENS_QUERY, (user_id, created))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
