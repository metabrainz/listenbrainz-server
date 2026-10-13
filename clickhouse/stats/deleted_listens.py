"""Apply listen deletions from the ListenBrainz listens database to ClickHouse.

New ``listen_delete_metadata`` and ``deleted_user_listen_history`` rows are copied over
(high-water mark in ``import_state``), their listens deleted and their users marked
for recompute. The rows are kept so that dump loads skip those listens. The
high-water mark only advances once the deletions are applied, so a failed run is
simply retried.
"""

import logging
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime

import psycopg2
from clickhouse_connect.driver import Client

from clickhouse.stats.cache_manager import mark_users_for_recompute
from clickhouse.stats.import_state import get_import_state, set_import_state
from clickhouse.utils import to_utc
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

# Listens in {table} of the deleted_listens records with id > last_id. `created` is part
# of the key: a re-submitted listen gets a new `created` and must stay.
DELETED_LISTENS_FILTER = """
    (user_id, listened_at, recording_msid, created) IN (
        SELECT user_id, listened_at, recording_msid, created
        FROM deleted_listens
        WHERE id > {{last_id:UInt64}}
    )
"""

# Listens in {table} of users whose history was deleted, up to the deletion's max_created
DELETED_USER_HISTORY_FILTER = """
    (user_id, created) IN (
        SELECT l.user_id, l.created
        FROM {table} AS l
        INNER JOIN (
            SELECT user_id, max(max_created) AS max_created
            FROM deleted_user_listen_history
            WHERE id > {{last_id:UInt64}}
            GROUP BY user_id
        ) AS d ON l.user_id = d.user_id
        WHERE l.created <= d.max_created
    )
"""


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
    listen_filter: str  # formatted with the listens table
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

DELETION_SOURCES = (DELETED_LISTENS, DELETED_USER_HISTORY)


def import_records(source: DeletionSource, listens_dsn: str, ch_client: Client, batch_size: int) -> tuple[int, int, int]:
    """Copy the source's new rows into ClickHouse; returns (rows, previous last id, new last id)."""
    last_id = get_import_state(ch_client, source.state_name)
    imported, max_id = 0, last_id
    for rows in _fetch_new_rows(listens_dsn, source.pg_query, last_id, batch_size):
        ch_client.insert(
            source.table,
            [tuple(to_utc(value) if isinstance(value, datetime) else value for value in row) for row in rows],
            column_names=list(source.columns),
        )
        imported += len(rows)
        max_id = max(max_id, rows[-1][0])
    return imported, last_id, max_id


def delete_listens(source: DeletionSource, ch_client: Client, last_id: int = 0, table: str = "listens") -> int:
    """Delete the listens in ``table`` of the source's records with id > last_id; returns how many."""
    listen_filter = source.listen_filter.format(table=table)
    parameters = {"last_id": last_id}
    count = ch_client.query(f"SELECT count() FROM {table} WHERE {listen_filter}", parameters=parameters).first_row[0]
    if count:
        ch_client.command(f"DELETE FROM {table} WHERE {listen_filter}", parameters=parameters)
    return count


def delete_all_deleted_listens(ch_client: Client, table: str) -> int:
    """Delete the listens in ``table`` of every deletion record, e.g. from a freshly loaded full dump."""
    return sum(delete_listens(source, ch_client, table=table) for source in DELETION_SOURCES)


def apply_deletions(source: DeletionSource, ch_client: Client, last_id: int) -> int:
    """Delete the listens of the source's records with id > last_id and mark their users stale."""
    count = delete_listens(source, ch_client, last_id)
    if count:
        users_query = f"SELECT DISTINCT user_id FROM {source.table} WHERE id > {{last_id:UInt64}}"
        mark_users_for_recompute(ch_client, users_query, {"last_id": last_id})
    return count


def import_deleted_listens(listens_dsn: str, ch_client: Client, batch_size: int = 10_000) -> dict:
    """Import and apply new deletions; returns a summary of the counts."""
    ensure_stats_schema(ch_client)
    start = time.monotonic()

    summary = {}
    for source in DELETION_SOURCES:
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
