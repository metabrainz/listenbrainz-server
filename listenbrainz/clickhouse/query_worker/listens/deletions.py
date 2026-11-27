"""Retain deletion metadata independently of dump age and PostgreSQL cleanup."""

from clickhouse_connect.driver import Client
from sqlalchemy import text
from sqlalchemy.engine import Engine

from listenbrainz.clickhouse.query_worker.listens.aggregates import send_changes


DELETION_IMPORT_BATCH_SIZE = 50_000
HISTORY_BATCH_SIZE = 1024


def sync_deletions(client: Client, listens_engine: Engine) -> None:
    # A pending request may complete after requests with larger IDs. Read all
    # completed keys and let ReplacingMergeTree coalesce repeated imports.
    queries = {
        "deleted_listens": """
            SELECT user_id, listened_at, recording_msid, listen_created::timestamptz(3)
              FROM listen_delete_metadata WHERE status = 'complete'
        """,
        "deleted_user_history": """
            SELECT user_id, max(max_created) FROM deleted_user_listen_history GROUP BY user_id
        """,
    }
    with listens_engine.connect() as connection:
        for table, query in queries.items():
            rows = connection.execution_options(stream_results=True).execute(text(query))
            for batch in rows.partitions(DELETION_IMPORT_BATCH_SIZE):
                client.insert(table, batch)


def delete_matching_listens(client, table, where, change_stream=None, parameters=None):
    if change_stream:
        # Send the values that still exist to every aggregate before removing them.
        send_changes(client, change_stream, table, -1, where, parameters)
    client.command(f"DELETE FROM {table} WHERE {where}", parameters=parameters, settings={"lightweight_deletes_sync": 2})


def apply_deletions(client, table, change_stream=None):
    """Remove matching versions before a full swap or incremental deduplication."""
    if client.query("SELECT 1 FROM deleted_listens LIMIT 1").result_rows:
        delete_matching_listens(client, table, """
            (user_id, listened_at, recording_msid, created) IN (
                SELECT user_id, listened_at, recording_msid, created FROM deleted_listens
            )
        """, change_stream)
    # Page over cutoff records in primary-key order. The mutation needs only
    # one cutoff per user, even for a user with millions of distinct listens.
    after_user = -1
    while True:
        batch = client.query("""
            SELECT user_id, toUnixTimestamp64Micro(max(max_created))
            FROM deleted_user_history WHERE user_id > {after:Int64}
            GROUP BY user_id ORDER BY user_id LIMIT {size:UInt32}
        """, parameters={"after": after_user, "size": HISTORY_BATCH_SIZE}).result_rows
        if not batch:
            break
        users, cutoffs = zip(*batch)
        delete_matching_listens(client, table, """
            user_id IN {users:Array(UInt32)}
              AND toUnixTimestamp64Micro(created) < transform(
                  user_id, {users:Array(UInt32)}, {cutoffs:Array(Int64)}, toInt64(0))
        """, change_stream, {"users": list(users), "cutoffs": list(cutoffs)})
        after_user = users[-1]
