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
before the deletion skip those listens (see load_dump.build_process_raw_listens_query).

The import state is only advanced after the deletions are applied, so a crash
in between is retried by the next run; both steps are idempotent.
"""

import logging
import time
from contextlib import closing
from dataclasses import dataclass
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
    with closing(psycopg2.connect(listens_dsn)) as pg_conn, \
            closing(pg_conn.cursor(name="clickhouse_deleted_listens_cursor")) as cursor:
        cursor.execute(query, (last_id,))
        while rows := cursor.fetchmany(batch_size):
            yield rows


@dataclass(frozen=True)
class DeletionSource:
    """A listens database table of deletions and the ClickHouse table it is copied to."""
    state_name: str  # import_state row holding the last copied id
    table: str
    pg_query: str
    columns: tuple[str, ...]
    # listens matching the records with id > {last_id:UInt64}
    listen_filter: str
    # keys of the import summary
    imported_key: str
    removed_key: str


DELETED_LISTENS = DeletionSource(
    state_name=DELETED_LISTENS_STATE,
    table="deleted_listens",
    pg_query=DELETED_LISTENS_PG_QUERY,
    columns=("id", "user_id", "listened_at", "recording_msid", "created"),
    listen_filter=DELETED_LISTENS_FILTER,
    imported_key="deleted_listens_imported",
    removed_key="deleted_listens_removed",
)

DELETED_USER_HISTORY = DeletionSource(
    state_name=DELETED_USER_HISTORY_STATE,
    table="deleted_user_listen_history",
    pg_query=DELETED_USER_HISTORY_PG_QUERY,
    columns=("id", "user_id", "max_created"),
    listen_filter=DELETED_USER_HISTORY_FILTER,
    imported_key="deleted_user_histories_imported",
    removed_key="deleted_user_listens_removed",
)


def import_records(source: DeletionSource, listens_dsn: str, ch_client: Client, batch_size: int) -> tuple[int, int, int]:
    """Copy the source's new rows from the listens database into ClickHouse.

    Returns (rows imported, previous last id, new last id).
    """
    last_id = get_import_state(ch_client, source.state_name)
    imported, max_id = 0, last_id
    for rows in _fetch_new_rows(listens_dsn, source.pg_query, last_id, batch_size):
        ch_client.insert(
            source.table,
            [tuple(_to_utc(value) for value in row) for row in rows],
            column_names=list(source.columns),
        )
        imported += len(rows)
        max_id = max(max_id, rows[-1][0])
    return imported, last_id, max_id


def apply_deletions(source: DeletionSource, ch_client: Client, last_id: int) -> int:
    """Remove the listens matching the source's records with id > last_id and mark their users stale.

    Returns the number of listens removed.
    """
    parameters = {"last_id": last_id}
    count = ch_client.query(
        f"SELECT count() FROM listens WHERE {source.listen_filter}", parameters=parameters
    ).first_row[0]
    if count == 0:
        return 0

    ch_client.command(f"DELETE FROM listens WHERE {source.listen_filter}", parameters=parameters)

    # force these users to be recomputed by the next stats job for every time range
    users_query = f"SELECT DISTINCT user_id FROM {source.table} WHERE id > {{last_id:UInt64}}"
    mark_users_for_recompute(ch_client, users_query, parameters)
    return count


def import_deleted_listens(listens_dsn: str, ch_client: Client, batch_size: int = 10_000) -> dict:
    """Import new deletions from the listens database and apply them to ClickHouse.

    Returns a summary dict with imported record counts and removed listen counts.
    """
    ensure_stats_schema(ch_client)
    start = time.monotonic()

    summary = {}
    for source in (DELETED_LISTENS, DELETED_USER_HISTORY):
        imported, prev_id, new_id = import_records(source, listens_dsn, ch_client, batch_size)
        removed = 0
        if imported:
            removed = apply_deletions(source, ch_client, prev_id)
            set_import_state(ch_client, source.state_name, new_id)
        summary[source.imported_key] = imported
        summary[source.removed_key] = removed

    summary["elapsed"] = time.monotonic() - start
    logger.info("Imported deleted listens: %s", summary)
    return summary
