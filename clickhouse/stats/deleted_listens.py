"""
Propagate listen deletions from the ListenBrainz listens database to ClickHouse.

Two sources, both read incrementally by primary key with the high-water mark
kept in ``import_state``:

- ``listen_delete_metadata`` (status = complete): individual listens deleted
  after they were submitted; identified by (user_id, listened_at, recording_msid,
  created).
- ``deleted_user_listen_history``: users whose whole listen history up to
  ``max_created`` was deleted.

For every new record the matching rows in ``listens`` are removed with a
lightweight DELETE and the affected users are marked for a forced recompute, so
the next stats job rewrites their stats even for ranges where no listens are left. The records themselves are kept in
``deleted_listens`` / ``deleted_user_listen_history`` so that dump loads created
before the deletion skip those listens (see load_dump.RAW_LISTENS_SOURCE).

The import state is only advanced after the deletions are applied, so a crash
in between is retried by the next run; both steps are idempotent.
"""

import logging
import time
from contextlib import suppress
from datetime import datetime, timezone

import psycopg2
from clickhouse_connect.driver import Client

from clickhouse.stats.cache_manager import mark_users_for_recompute
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

DELETED_LISTENS_STATE = "listen_delete_metadata"
DELETED_USER_HISTORY_STATE = "deleted_user_listen_history"

DELETED_LISTENS_PG_QUERY = """
    SELECT id
         , user_id
         , listened_at
         , recording_msid::text
         , listen_created
      FROM listen_delete_metadata
     WHERE status = 'complete'::listen_delete_metadata_status_enum
       AND id > %s
  ORDER BY id
"""

DELETED_USER_HISTORY_PG_QUERY = """
    SELECT id, user_id, max_created
      FROM deleted_user_listen_history
     WHERE id > %s
  ORDER BY id
"""

# listens matching newly imported deleted_listens records (id > last applied id).
# `created` is part of the key: a listen deleted and re-submitted later has a new
# `created` and must not be removed by the older deletion record.
DELETED_LISTENS_FILTER = """
    (user_id, listened_at, recording_msid, created) IN (
        SELECT user_id, listened_at, recording_msid, created
        FROM deleted_listens
        WHERE id > {last_id:UInt64}
    )
"""

# listens of users whose history was deleted, up to the deletion's max_created
DELETED_USER_HISTORY_FILTER = """
    (user_id, created) IN (
        SELECT l.user_id, l.created
        FROM listens AS l
        INNER JOIN (
            SELECT user_id, max(max_created) AS max_created
            FROM deleted_user_listen_history
            WHERE id > {last_id:UInt64}
            GROUP BY user_id
        ) AS d ON l.user_id = d.user_id
        WHERE l.created <= d.max_created
    )
"""


def _to_utc(value):
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def get_import_state(ch_client: Client, name: str) -> int:
    result = ch_client.query(
        "SELECT last_id FROM import_state FINAL WHERE name = {name:String}",
        parameters={"name": name},
    )
    return result.first_row[0] if result.result_rows else 0


def set_import_state(ch_client: Client, name: str, last_id: int) -> None:
    ch_client.command(
        "INSERT INTO import_state (name, last_id) VALUES ({name:String}, {last_id:UInt64})",
        parameters={"name": name, "last_id": last_id},
    )


def _fetch_new_rows(listens_dsn: str, query: str, last_id: int, batch_size: int):
    """Yield batches of rows with id > last_id from the listens database using a server-side cursor."""
    pg_conn = None
    cursor = None
    try:
        pg_conn = psycopg2.connect(listens_dsn)
        cursor = pg_conn.cursor(name="clickhouse_deleted_listens_cursor")
        cursor.execute(query, (last_id,))
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield rows
    finally:
        if cursor is not None:
            with suppress(Exception):
                cursor.close()
        if pg_conn is not None:
            with suppress(Exception):
                pg_conn.close()


def import_deleted_listens_records(listens_dsn: str, ch_client: Client, batch_size: int) -> tuple[int, int, int]:
    """Copy new listen_delete_metadata rows into ClickHouse deleted_listens.

    Returns (rows imported, previous last id, new last id).
    """
    last_id = get_import_state(ch_client, DELETED_LISTENS_STATE)
    imported, max_id = 0, last_id
    for rows in _fetch_new_rows(listens_dsn, DELETED_LISTENS_PG_QUERY, last_id, batch_size):
        ch_client.insert(
            "deleted_listens",
            [(row[0], row[1], _to_utc(row[2]), row[3], _to_utc(row[4])) for row in rows],
            column_names=["id", "user_id", "listened_at", "recording_msid", "created"],
        )
        imported += len(rows)
        max_id = max(max_id, rows[-1][0])
    return imported, last_id, max_id


def import_deleted_user_history_records(listens_dsn: str, ch_client: Client, batch_size: int) -> tuple[int, int, int]:
    """Copy new deleted_user_listen_history rows into ClickHouse.

    Returns (rows imported, previous last id, new last id).
    """
    last_id = get_import_state(ch_client, DELETED_USER_HISTORY_STATE)
    imported, max_id = 0, last_id
    for rows in _fetch_new_rows(listens_dsn, DELETED_USER_HISTORY_PG_QUERY, last_id, batch_size):
        ch_client.insert(
            "deleted_user_listen_history",
            [(row[0], row[1], _to_utc(row[2])) for row in rows],
            column_names=["id", "user_id", "max_created"],
        )
        imported += len(rows)
        max_id = max(max_id, rows[-1][0])
    return imported, last_id, max_id


def _apply_deletions(ch_client: Client, listen_filter: str, last_id: int, users_query: str) -> int:
    """Remove the listens matching ``listen_filter`` and mark their users stale.

    Returns the number of listens removed.
    """
    parameters = {"last_id": last_id}
    count = ch_client.query(
        f"SELECT count() FROM listens WHERE {listen_filter}", parameters=parameters
    ).first_row[0]
    if count == 0:
        return 0

    ch_client.command(f"DELETE FROM listens WHERE {listen_filter}", parameters=parameters)

    # force these users to be recomputed by the next stats job for every time range
    mark_users_for_recompute(ch_client, users_query, parameters)
    return count


def apply_deleted_listens(ch_client: Client, last_id: int) -> int:
    """Apply deleted_listens records with id > last_id to listens."""
    return _apply_deletions(
        ch_client,
        DELETED_LISTENS_FILTER,
        last_id,
        "SELECT DISTINCT user_id FROM deleted_listens WHERE id > {last_id:UInt64}",
    )


def apply_deleted_user_history(ch_client: Client, last_id: int) -> int:
    """Apply deleted_user_listen_history records with id > last_id to listens."""
    return _apply_deletions(
        ch_client,
        DELETED_USER_HISTORY_FILTER,
        last_id,
        "SELECT DISTINCT user_id FROM deleted_user_listen_history WHERE id > {last_id:UInt64}",
    )


def import_deleted_listens(listens_dsn: str, ch_client: Client, batch_size: int = 10_000) -> dict:
    """Import new deletions from the listens database and apply them to ClickHouse.

    Returns a summary dict with imported record counts and removed listen counts.
    """
    ensure_stats_schema(ch_client)
    start = time.monotonic()

    imported_listens, prev_listen_id, new_listen_id = import_deleted_listens_records(listens_dsn, ch_client, batch_size)
    removed_listens = 0
    if imported_listens:
        removed_listens = apply_deleted_listens(ch_client, prev_listen_id)
        set_import_state(ch_client, DELETED_LISTENS_STATE, new_listen_id)

    imported_users, prev_user_id, new_user_id = import_deleted_user_history_records(listens_dsn, ch_client, batch_size)
    removed_user_listens = 0
    if imported_users:
        removed_user_listens = apply_deleted_user_history(ch_client, prev_user_id)
        set_import_state(ch_client, DELETED_USER_HISTORY_STATE, new_user_id)

    summary = {
        "deleted_listens_imported": imported_listens,
        "deleted_listens_removed": removed_listens,
        "deleted_user_histories_imported": imported_users,
        "deleted_user_listens_removed": removed_user_listens,
        "elapsed": time.monotonic() - start,
    }
    logger.info("Imported deleted listens: %s", summary)
    return summary
