"""Database helpers for the user-partitioned listens database."""

import logging
import time
from typing import Optional, Sequence

import psycopg2
import sqlalchemy
from more_itertools.more import chunked
from psycopg2.extras import NamedTupleCursor, execute_values
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


logger = logging.getLogger(__name__)

engine: Optional[sqlalchemy.engine.Engine] = None


INSERT_LISTENS_QUERY = """
    WITH inserted AS (
        INSERT INTO listen (listened_at, created, user_id, recording_msid, data)
             VALUES %s
        ON CONFLICT (user_id, listened_at, recording_msid)
          DO NOTHING
          RETURNING listened_at, user_id, recording_msid
    ), counts AS (
        INSERT INTO listen_user_metadata AS lum (user_id, count, min_listened_at, max_listened_at)
             SELECT user_id, count(*), min(listened_at), max(listened_at)
               FROM inserted
           GROUP BY user_id
           ORDER BY user_id
        ON CONFLICT (user_id)
          DO UPDATE SET count = lum.count + excluded.count
                      , min_listened_at = least(lum.min_listened_at, excluded.min_listened_at)
                      , max_listened_at = greatest(lum.max_listened_at, excluded.max_listened_at)
    )
    SELECT listened_at, user_id, recording_msid::TEXT FROM inserted
"""

DELETE_USER_LISTENS_QUERY = "DELETE FROM listen WHERE user_id = %s AND created <= %s"

LOCK_LISTEN_METADATA_QUERY = """
    INSERT INTO listen_user_metadata AS lum (user_id, count)
         SELECT user_id, 0
           FROM unnest(%s::INTEGER[]) AS u(user_id)
       ORDER BY user_id
    ON CONFLICT (user_id)
      DO UPDATE SET count = lum.count
"""

REFRESH_LISTEN_METADATA_QUERY = """
    UPDATE listen_user_metadata lm
       SET count = (SELECT count(*) FROM listen l WHERE l.user_id = lm.user_id)
         , min_listened_at = (SELECT min(listened_at) FROM listen l WHERE l.user_id = lm.user_id)
         , max_listened_at = (SELECT max(listened_at) FROM listen l WHERE l.user_id = lm.user_id)
     WHERE lm.user_id = ANY(%s)
"""

REFRESH_LISTEN_BOUNDS_QUERY = """
    UPDATE listen_user_metadata lm
       SET min_listened_at = (SELECT min(listened_at) FROM listen l WHERE l.user_id = lm.user_id)
         , max_listened_at = (SELECT max(listened_at) FROM listen l WHERE l.user_id = lm.user_id)
     WHERE lm.user_id = ANY(%s)
"""

# Users without a metadata row are always stale, so skip their scans here (CASE does not
# evaluate the subqueries) rather than counting their histories twice.
STORED_AND_ACTUAL_LISTEN_COUNTS_QUERY = """
    SELECT u.user_id
         , lm.count AS stored_count
         , lm.min_listened_at AS stored_min
         , lm.max_listened_at AS stored_max
         , CASE WHEN lm.user_id IS NOT NULL
                THEN (SELECT count(*) FROM listen l WHERE l.user_id = u.user_id)
           END AS actual_count
         , CASE WHEN lm.user_id IS NOT NULL
                THEN (SELECT min(listened_at) FROM listen l WHERE l.user_id = u.user_id)
           END AS actual_min
         , CASE WHEN lm.user_id IS NOT NULL
                THEN (SELECT max(listened_at) FROM listen l WHERE l.user_id = u.user_id)
           END AS actual_max
      FROM unnest(%s::INTEGER[]) AS u(user_id)
 LEFT JOIN listen_user_metadata lm
        ON lm.user_id = u.user_id
"""

DELETE_PENDING_LISTENS_ADVISORY_LOCK = 72419302
RECALCULATE_BATCH_SIZE = 100
# Listens per insert transaction, bounds statement size for large dump imports
INSERT_BATCH_SIZE = 1000


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
        logger.warning("Listens database is not configured; listens cannot be read, ingested or deleted.")
        return

    while True:
        try:
            engine = create_engine(connect_str, poolclass=poolclass, **engine_kwargs)
            break
        except psycopg2.OperationalError as e:
            print("Couldn't establish connection to listens database: {}".format(str(e)))
            print("Sleeping 2 seconds and trying again...")
            time.sleep(2)


def insert(rows: Sequence[tuple]) -> list[tuple]:
    """Insert listens and update their users' counts and timestamp bounds atomically.

    Returns (listened_at, user_id, recording_msid) of the newly inserted listens,
    listens absent from the result were duplicates.

    Aggregate INSERT ... RETURNING rather than the input batch so duplicates do
    not increase counts. Add each delta to the current metadata row in the upsert:
    a count computed from a snapshot could miss concurrent ingestion and overwrite
    its updates. LEAST/GREATEST similarly widen timestamp bounds without rescanning
    the user's history. Concurrent upserts serialize on the affected metadata rows.

    Use a single statement per transaction so metadata rows are locked in user_id
    order, and only after all its listens are inserted. Paging one transaction over
    several statements would hold earlier pages' metadata locks while later inserts
    wait on listens being deleted, which can deadlock with deletions. Large batches
    (dump imports) are committed in chunks instead; a retry skips the duplicates.
    """
    if not rows:
        return []
    if engine is None:
        raise RuntimeError("Listens database is required for ingestion")

    inserted = []
    connection = engine.raw_connection()
    try:
        for chunk in chunked(rows, INSERT_BATCH_SIZE):
            with connection.cursor() as cursor:
                inserted.extend(execute_values(
                    cursor,
                    INSERT_LISTENS_QUERY,
                    chunk,
                    template="(%s::timestamptz, %s::timestamptz, %s::integer, %s::uuid, %s::jsonb)",
                    page_size=len(chunk),
                    fetch=True,
                ))
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return inserted


def delete_pending_listens() -> list[int]:
    """Delete pending listens and retain every request and its result atomically.

    Returns the ids of users whose listens were deleted, so callers can invalidate their caches.

    Materialize and lock pending requests so deletion and status updates use the
    same request set. Count DELETE ... RETURNING rows, not requests: duplicate or
    invalid requests must not decrement the count more than once per deleted listen.
    Apply negative deltas to the current metadata counts rather than replacing them
    with snapshot counts that could overwrite concurrent ingestion. This also avoids
    recounting a user's full history for a small deletion. Metadata upserts acquire
    row locks in user_id order. The delta itself is negative, not subtracted in the
    update, so a user without a metadata row gets an obviously invalid negative
    count for recalculation to repair, rather than a plausible but wrong one.

    Deleting an endpoint can shrink timestamp bounds, so recompute those separately
    while the metadata locks remain held. Under READ COMMITTED, the next statement
    gets a fresh snapshot that sees this transaction's deletions and ingestion that
    committed before we acquired the locks. Ingestion still waiting on those locks
    applies its deltas and widens the bounds after we commit.

    Keep the advisory lock to skip overlapping cron runs rather than have multiple
    workers compete for the same pending-request row locks. It is nonblocking and
    transaction-scoped, so commit or rollback releases it. Ingestion does not acquire
    this advisory lock; only updates to the same metadata rows must wait.
    """
    if engine is None:
        raise RuntimeError("Listens database is required to process deletions")
    with engine.begin() as connection:
        if not connection.execute(
            sqlalchemy.text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
            {"lock_key": DELETE_PENDING_LISTENS_ADVISORY_LOCK},
        ).scalar():
            return []
        user_ids = connection.execute(sqlalchemy.text("""
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
            ), counts AS (
           INSERT INTO listen_user_metadata AS lum (user_id, count)
                SELECT user_id, -count(*)
                  FROM deleted
              GROUP BY user_id
              ORDER BY user_id
           ON CONFLICT (user_id)
             DO UPDATE
                   SET count = lum.count + excluded.count
             RETURNING user_id
            ), marked AS (
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
            )
            SELECT user_id FROM counts
        """)).scalars().all()
        if user_ids:
            connection.exec_driver_sql(REFRESH_LISTEN_BOUNDS_QUERY, (user_ids,))
    return user_ids


def delete_user(user_id: int, created, delete_metadata: bool = False):
    """Delete a user's listens through the cutoff and record it until dump cleanup.

    Delete the listens before locking the user's metadata row, so ingestion for this
    user is not blocked for the duration of a potentially huge delete. This also takes
    locks in the same order as delete_pending_listens (listen rows, then metadata),
    which avoids deadlocks between the two. Then lock the metadata row using the
    protocol of _refresh_listen_metadata and recount the remaining listens rather than
    relying on the old count, so this also repairs stale metadata. The lock waits for
    ingestion that committed during the delete, and the recount's fresh snapshot sees
    it. Only listens created after the cutoff remain, usually making this cheaper than
    a full-history recount. Refresh timestamp bounds in the same transaction so they
    can shrink or become NULL when no listens remain.

    delete_metadata removes the metadata row instead, for account deletion.
    """
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
            if delete_metadata:
                cursor.execute("DELETE FROM listen_user_metadata WHERE user_id = %s", (user_id,))
            else:
                _refresh_listen_metadata(cursor, [user_id])
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_missing_to_listen_user_metadata(user_ids: Sequence[int]):
    """Create zero listen count rows for the given users unless they already have one."""
    if engine is None:
        raise RuntimeError("Listens database is required to store listen counts")
    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            execute_values(
                cursor,
                "INSERT INTO listen_user_metadata (user_id, count) VALUES %s ON CONFLICT (user_id) DO NOTHING",
                [(user_id,) for user_id in sorted(user_ids)],
                template="(%s, 0)",
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _refresh_listen_metadata(cursor, user_ids: Sequence[int]):
    """Recompute listen counts and timestamp bounds in the caller's transaction.

    The seemingly redundant SET count = lum.count is a locking upsert: it creates
    missing rows and locks existing ones without changing their counts. SELECT FOR
    UPDATE alone would not protect a user whose metadata row does not yet exist.
    Acquire metadata locks in user_id order to avoid inconsistent lock ordering.

    Locking and recounting must be separate statements under READ COMMITTED. If an
    ingestion transaction holds a metadata lock, wait for it first, then take a fresh
    snapshot for the recount. Combining both steps in one statement could retain a
    snapshot from before the wait and overwrite that ingestion's count. Later inserts
    cannot commit their metadata updates until the caller commits or rolls back, and
    then apply their deltas on top of the refreshed values.

    Per-user scalar subqueries keep zero-listen users in the update (count zero and
    NULL bounds) and let timestamp extrema use the user/listened_at index separately
    from the count scan. The scans need no explicit listen-row locks; the metadata
    row locks coordinate with ingestion until the caller finishes the transaction.
    """
    cursor.execute(LOCK_LISTEN_METADATA_QUERY, (user_ids,))
    cursor.execute(REFRESH_LISTEN_METADATA_QUERY, (user_ids,))


def recalculate_listen_counts(user_ids: Sequence[int]):
    """Correct the listen counts and bounds of the given users, creating missing rows.

    First compare stored metadata with actual counts and timestamp bounds in one
    statement snapshot, without taking row locks. Users without a metadata row are
    stale without counting them first. Normal ingestion changes listens
    and metadata atomically, so healthy users need no repair and no metadata lock.
    The LEFT JOIN also identifies users whose metadata row is missing.

    Treat this comparison only as a list of repair candidates: ingestion can commit
    after it runs. _refresh_listen_metadata locks only those candidates and recomputes
    from a fresh snapshot rather than writing back the earlier observations. Sort and
    deduplicate users for consistent metadata lock ordering, and commit each small
    batch to limit how long ingestion for affected users has to wait.
    """
    if engine is None:
        raise RuntimeError("Listens database is required to store listen counts")
    user_ids = sorted(set(user_ids))
    connection = engine.raw_connection()
    try:
        corrected = 0
        for idx, batch in enumerate(chunked(user_ids, RECALCULATE_BATCH_SIZE)):
            with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
                cursor.execute(STORED_AND_ACTUAL_LISTEN_COUNTS_QUERY, (batch,))
                stale = [
                    row.user_id for row in cursor.fetchall()
                    if row.stored_count is None
                    or (row.stored_count, row.stored_min, row.stored_max)
                    != (row.actual_count, row.actual_min, row.actual_max)
                ]
                if stale:
                    _refresh_listen_metadata(cursor, stale)
            connection.commit()
            corrected += len(stale)
            if idx % 100 == 0:
                logger.info("Recalculated listen counts for %d of %d users, corrected %d",
                            idx * RECALCULATE_BATCH_SIZE + len(batch), len(user_ids), corrected)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
