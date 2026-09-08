""" Migrate listens from timescale (SQLALCHEMY_TIMESCALE_URI) to a plain postgres database
(SQLALCHEMY_LISTENS_URI) where listens are hash-partitioned by user_id.

Once the unique index exists on the target, copies use ON CONFLICT DO UPDATE (only when the source
row is newer) so re-runs are idempotent and a listen re-submitted after being deleted picks up its
new `created`. Before the index exists (initial bulk load) plain inserts are used and each
listened_at window is committed as a whole: if a full run dies, resume it with
--start <start of the window that was running>. Do not re-run a full copy over windows that
completed while the unique index did not exist yet.

`created` defaults to the transaction start time, so subtract a small overlap from the logged
checkpoint when passing it as --since. Deletes are not propagated by the copies, replay-deletes
applies listen_delete_metadata (status = 'complete') and deleted_user_listen_history to the target.
Its logged --since-id / --since-history-id already include an overlap of DELETE_ID_OVERLAP rows
because rows whose id was allocated but not committed yet when the checkpoint was read would
otherwise be skipped forever. Replays are idempotent so re-applying them is harmless.

Before runtime dual writes are deployed, each cycle should run replay-deletes before incremental.
After dual writes are active, new listen and user deletes are applied directly to both databases;
replay-deletes remains necessary for historical deletes and any gap from before that deployment.
A listen re-submitted while delete_listens is mid-run can end up in timescale only, so keep
running incremental after dual writes are live.
"""
import os
import re
import time
from datetime import datetime, timedelta, timezone

import click
import psycopg2
import psycopg2.extras
from flask import current_app
from psycopg2.extras import execute_values

from listenbrainz.webserver import create_app

psycopg2.extras.register_uuid()

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "admin", "listens")
CREATE_TABLES_SQL_FILE = os.path.join(ADMIN_SQL_DIR, "create_tables.sql")
CREATE_INDEXES_SQL_FILE = os.path.join(ADMIN_SQL_DIR, "create_indexes.sql")

PARTITION_COUNT = 256
DEFAULT_BATCH_SIZE = 10000
DEFAULT_WINDOW = timedelta(days=30)
# number of ids subtracted from the logged delete checkpoints, see the module docstring
DELETE_ID_OVERLAP = 1000
# comparing a range that has not been copied yet mismatches on every user, cap the per-window detail
MAX_LOGGED_DISCREPANCIES_PER_WINDOW = 20
UNIQUE_INDEX_NAME = "user_id_listened_at_recording_msid_ndx_listen"

CREATE_PARTITION_SQL = """
    CREATE TABLE IF NOT EXISTS listen_p{index:03d}
    PARTITION OF listen FOR VALUES WITH (MODULUS {modulus}, REMAINDER {index})
"""
PARTITION_BOUND_RE = re.compile(r"MODULUS\s+(\d+)\s*,\s*REMAINDER\s+(\d+)", re.IGNORECASE)

# data is passed through as text to avoid decoding / re-encoding json for every row
SELECT_COLUMNS = "listened_at, created, user_id, recording_msid, data::text"
INSERT_TEMPLATE = "(%s, %s, %s, %s, %s::jsonb)"
INSERT_SQL = "INSERT INTO listen (listened_at, created, user_id, recording_msid, data) VALUES %s"
# a listen deleted and re-submitted in timescale has a newer created, take it over so that
# replay-deletes (which matches on created) does not remove the re-submitted listen
INSERT_ON_CONFLICT_SQL = INSERT_SQL + """
    ON CONFLICT (user_id, listened_at, recording_msid)
    DO UPDATE SET created = EXCLUDED.created, data = EXCLUDED.data
    WHERE EXCLUDED.created > listen.created
"""

# 'pending' rows still exist in timescale, only replay rows that have actually been deleted there.
# matching on created too leaves a listen re-submitted after the delete alone.
SELECT_LISTEN_DELETES_SQL = """
    SELECT user_id, listened_at, recording_msid, listen_created
      FROM listen_delete_metadata
     WHERE id > %s
       AND status = 'complete'
  ORDER BY id
"""
REPLAY_LISTEN_DELETES_SQL = """
    DELETE FROM listen l
     USING (VALUES %s) AS d (user_id, listened_at, recording_msid, listen_created)
     WHERE l.user_id = d.user_id
       AND l.listened_at = d.listened_at
       AND l.recording_msid = d.recording_msid
       AND l.created <= d.listen_created
"""
REPLAY_LISTEN_DELETES_TEMPLATE = "(%s::int, %s::timestamptz, %s::uuid, %s::timestamptz)"
SELECT_USER_DELETES_SQL = "SELECT user_id, max_created FROM deleted_user_listen_history WHERE id > %s ORDER BY id"
REPLAY_USER_DELETES_SQL = "DELETE FROM listen WHERE user_id = %s AND created <= %s"

# a pending row may become 'complete' later, so the next watermark is just below the oldest pending row
DELETE_CHECKPOINT_SQL = """
    SELECT COALESCE(min(id) FILTER (WHERE status = 'pending') - 1, max(id), 0)
      FROM listen_delete_metadata
"""
USER_DELETE_CHECKPOINT_SQL = "SELECT COALESCE(max(id), 0) FROM deleted_user_listen_history"
TARGET_INTEGRITY_SQL = """
    SELECT COALESCE(sum(listen_count), 0)::bigint AS total_listens,
           COALESCE(sum(listen_count - 1), 0)::bigint AS duplicate_listens,
           count(*) FILTER (WHERE listen_count > 1) AS duplicate_keys
      FROM (
            SELECT count(*) AS listen_count
              FROM listen
          GROUP BY user_id, listened_at, recording_msid
           ) listens_by_key
"""

# Keep listened_at as a simple range predicate so TimescaleDB can exclude chunks. The created
# predicate makes the compared data immutable with respect to new writes, while ordering the
# already-aggregated rows lets the caller compare both databases without retaining every user's
# count in memory. Aggregating one window at a time keeps each query and its sort bounded, asking
# either database for a single aggregate over the whole listen range would stall it. The target has
# no index covering listened_at (see admin/listens/create_indexes.sql), so each window costs a scan
# of it: compare a range no wider than the migration actually needs verified.
LISTEN_COUNTS_BY_USER_SQL = """
    SELECT user_id, count(*)::bigint AS listen_count
      FROM listen
     WHERE listened_at >= %s
       AND listened_at < %s
       AND created < %s
  GROUP BY user_id
  ORDER BY user_id
"""


def _uri(name):
    # consul renders SERVICEDOESNOTEXIST_... when the database service is not registered and
    # KEYDOESNOTEXIST_... into the uri when one of its keys is missing
    uri = current_app.config.get(name)
    if not uri or uri.startswith("SERVICEDOESNOTEXIST") or "KEYDOESNOTEXIST" in uri:
        raise click.UsageError(f"{name} is not set in the config")
    return uri


def connect_source():
    return psycopg2.connect(_uri("SQLALCHEMY_TIMESCALE_URI"))


def connect_target():
    return psycopg2.connect(_uri("SQLALCHEMY_LISTENS_URI"))


def _parse_ts(value):
    if value is None:
        return None
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _read_sql(path):
    with open(path) as f:
        return f.read()


def _fetch_one(conn, query, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    conn.rollback()
    return row


def _existing_partitions(cur):
    """ Return (modulus, count) of the existing hash partitions of the listen table. """
    cur.execute("""
        SELECT pg_get_expr(c.relpartbound, c.oid)
          FROM pg_inherits i
          JOIN pg_class c ON c.oid = i.inhrelid
         WHERE i.inhparent = 'listen'::regclass
    """)
    bounds = [row[0] for row in cur.fetchall()]  # FOR VALUES WITH (modulus 256, remainder 3)
    if not bounds:
        return None, 0
    moduli = set()
    for bound in bounds:
        match = PARTITION_BOUND_RE.search(bound)
        if match is None:
            raise click.ClickException(f"listen table has a partition that is not a hash partition: {bound}")
        moduli.add(int(match.group(1)))
    if len(moduli) != 1:
        raise click.ClickException(f"listen table has partitions with mixed moduli: {sorted(moduli)}")
    return moduli.pop(), len(bounds)


def create_schema(partition_count):
    logger = current_app.logger
    with connect_target() as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('listen')")
        if cur.fetchone()[0] is None:
            cur.execute(_read_sql(CREATE_TABLES_SQL_FILE))
            logger.info("created listen table")
        else:
            logger.info("listen table already exists")

        modulus, existing = _existing_partitions(cur)
        if existing and modulus != partition_count:
            raise click.ClickException(
                f"listen table already has {existing} partitions with modulus {modulus}, "
                f"refusing to create partitions with modulus {partition_count}"
            )
        if existing:
            logger.info("listen table already has %d of %d partitions, creating the missing ones", existing, partition_count)
        for index in range(partition_count):
            cur.execute(CREATE_PARTITION_SQL.format(index=index, modulus=partition_count))
        conn.commit()
    logger.info("listen table has %d partitions", partition_count)


def create_indexes():
    with connect_target() as conn, conn.cursor() as cur:
        cur.execute(_read_sql(CREATE_INDEXES_SQL_FILE))
        conn.commit()
    current_app.logger.info("created listen indexes")


def _insert_sql(target_conn, require_unique=False):
    """ Use ON CONFLICT DO UPDATE if the unique index exists, otherwise a plain insert. """
    row = _fetch_one(target_conn, "SELECT 1 FROM pg_indexes WHERE tablename = 'listen' AND indexname = %s",
                     (UNIQUE_INDEX_NAME,))
    if row:
        return INSERT_ON_CONFLICT_SQL
    if require_unique:
        raise click.ClickException(
            f"unique index {UNIQUE_INDEX_NAME} does not exist on the target; "
            "run create-indexes successfully before running an incremental migration"
        )
    current_app.logger.warning("unique index %s does not exist on the target yet, using plain inserts: "
                               "re-running or overlapping copies will create duplicate listens", UNIQUE_INDEX_NAME)
    return INSERT_SQL


def _log_checkpoint(source_conn):
    """ Log max(created) of the source at the start of a run, the --since for the next incremental run. """
    max_created = _fetch_one(source_conn, "SELECT max(created) FROM listen")[0]
    current_app.logger.info("max(created) in source at start of run: %s, use it (minus a small overlap) as --since "
                            "for the next incremental run", max_created.isoformat() if max_created else None)
    return max_created


def copy_batches(source_conn, target_conn, query, params, write_sql, write_template, batch_size, cursor_name,
                 commit_every_batch=True):
    """ Stream rows from source using a server side cursor and apply them to the target in batches
    with execute_values(write_sql, rows, template=write_template).

    If commit_every_batch is False, all batches are committed together at the end instead.
    Returns (rows_read, rows_affected). """
    read = affected = 0
    with source_conn.cursor(name=cursor_name) as src_cur:
        src_cur.itersize = batch_size
        src_cur.execute(query, params)
        while True:
            rows = src_cur.fetchmany(batch_size)
            if not rows:
                break
            with target_conn.cursor() as dst_cur:
                execute_values(dst_cur, write_sql, rows, template=write_template, page_size=batch_size)
                affected += dst_cur.rowcount
            if commit_every_batch:
                target_conn.commit()
            read += len(rows)
    target_conn.commit()
    source_conn.rollback()  # end the server side cursor's transaction
    return read, affected


def migrate_full(start, end, window, batch_size):
    """ Copy all listens from timescale, one listened_at window at a time. """
    logger = current_app.logger
    source_conn = connect_source()
    target_conn = connect_target()
    try:
        max_created = _log_checkpoint(source_conn)
        insert_sql = _insert_sql(target_conn)

        if start is None or end is None:
            min_ts, max_ts = _fetch_one(source_conn, "SELECT min(listened_at), max(listened_at) FROM listen")
            if min_ts is None:
                logger.info("no listens found in source, nothing to do")
                return
            start = start or min_ts
            end = end or (max_ts + timedelta(seconds=1))

        query = f"SELECT {SELECT_COLUMNS} FROM listen WHERE listened_at >= %s AND listened_at < %s"

        total_read = total_inserted = 0
        window_start = start
        overall_t0 = time.monotonic()
        while window_start < end:
            window_end = min(window_start + window, end)
            logger.info("copying window %s -> %s (resume with --start %s if this run dies)",
                        window_start.isoformat(), window_end.isoformat(), window_start.isoformat())
            t0 = time.monotonic()
            # a window is committed as a whole so that a crashed run can be resumed at the logged
            # window start without duplicating listens (there is no unique index during the full copy)
            read, inserted = copy_batches(source_conn, target_conn, query, (window_start, window_end),
                                          insert_sql, INSERT_TEMPLATE, batch_size, "migrate_listens_full",
                                          commit_every_batch=False)
            total_read += read
            total_inserted += inserted
            logger.info("window %s -> %s: read %d, inserted %d (%.1fs) | total read %d, inserted %d",
                        window_start.isoformat(), window_end.isoformat(), read, inserted,
                        time.monotonic() - t0, total_read, total_inserted)
            window_start = window_end
        logger.info("full migration complete: read %d, inserted %d in %.1fs, "
                    "next --since: %s (subtract a small overlap from this value)",
                    total_read, total_inserted, time.monotonic() - overall_t0,
                    max_created.isoformat() if max_created else None)
    finally:
        source_conn.close()
        target_conn.close()


def migrate_incremental(since, until, batch_size):
    """ Copy all listens created at or after `since` (and before `until` if given). """
    source_conn = connect_source()
    target_conn = connect_target()
    try:
        max_created = _log_checkpoint(source_conn)
        insert_sql = _insert_sql(target_conn, require_unique=True)

        query = f"SELECT {SELECT_COLUMNS} FROM listen WHERE created >= %s"
        params = [since]
        if until is not None:
            query += " AND created < %s"
            params.append(until)

        t0 = time.monotonic()
        read, inserted = copy_batches(source_conn, target_conn, query, params, insert_sql, INSERT_TEMPLATE,
                                      batch_size, "migrate_listens_incremental")
        current_app.logger.info(
            "incremental migration complete (created >= %s%s): read %d, inserted/updated %d in %.1fs, "
            "next --since: %s (subtract a small overlap from this value)",
            since.isoformat(), f", < {until.isoformat()}" if until else "", read, inserted,
            time.monotonic() - t0, max_created.isoformat() if max_created else None
        )
    finally:
        source_conn.close()
        target_conn.close()


def replay_deletes(since_id, since_history_id, batch_size):
    """ Replay listen / user deletes recorded in timescale against the target database. """
    logger = current_app.logger
    source_conn = connect_source()
    target_conn = connect_target()
    try:
        # checkpoints are taken before reading so that rows added / completed during the run are
        # picked up by the next run. rows whose id was allocated but not committed yet at this point
        # are invisible to this run, hence the overlap.
        next_since_id = max(_fetch_one(source_conn, DELETE_CHECKPOINT_SQL)[0] - DELETE_ID_OVERLAP, 0)
        next_since_history_id = max(_fetch_one(source_conn, USER_DELETE_CHECKPOINT_SQL)[0] - DELETE_ID_OVERLAP, 0)
        t0 = time.monotonic()

        listens_read, listens_deleted = copy_batches(
            source_conn, target_conn, SELECT_LISTEN_DELETES_SQL, (since_id,),
            REPLAY_LISTEN_DELETES_SQL, REPLAY_LISTEN_DELETES_TEMPLATE, batch_size, "migrate_listens_replay_deletes"
        )
        logger.info("replayed %d listen deletes (id > %d), deleted %d listens", listens_read, since_id, listens_deleted)

        with source_conn.cursor() as src_cur:
            src_cur.execute(SELECT_USER_DELETES_SQL, (since_history_id,))
            user_rows = src_cur.fetchall()
        source_conn.rollback()
        users_deleted = 0
        for user_id, max_created in user_rows:
            with target_conn.cursor() as dst_cur:
                dst_cur.execute(REPLAY_USER_DELETES_SQL, (user_id, max_created))
                users_deleted += dst_cur.rowcount
            target_conn.commit()
        logger.info("replayed %d user deletes (id > %d), deleted %d listens", len(user_rows), since_history_id, users_deleted)

        logger.info("replay deletes complete in %.1fs, next run: --since-id %d --since-history-id %d",
                    time.monotonic() - t0, next_since_id, next_since_history_id)
    finally:
        source_conn.close()
        target_conn.close()


def check_integrity():
    """ Check that the target is fully partitioned and contains no duplicate logical listens. """
    target_conn = connect_target()
    try:
        with target_conn.cursor() as cur:
            cur.execute("SELECT to_regclass('listen')")
            if cur.fetchone()[0] is None:
                raise click.ClickException("listen table does not exist on the target; run create-schema first")

            modulus, partition_count = _existing_partitions(cur)
            if partition_count != modulus:
                raise click.ClickException(
                    f"listen table has {partition_count} of {modulus or 0} required hash partitions; "
                    "run create-schema with the original partition count"
                )

            cur.execute(TARGET_INTEGRITY_SQL)
            total_listens, duplicate_listens, duplicate_keys = cur.fetchone()
        target_conn.rollback()
    finally:
        target_conn.close()

    if duplicate_listens:
        raise click.ClickException(
            f"target integrity check failed: found {duplicate_listens} duplicate listens "
            f"across {duplicate_keys} logical listen keys"
        )
    current_app.logger.info(
        "target integrity check passed: %d listens, %d complete hash partitions, no duplicates",
        total_listens, partition_count
    )


def _merge_user_counts(source_rows, target_rows):
    """Yield (user_id, source_count, target_count) for the union of two user count streams.

    Both inputs must be ordered by user_id. A user missing from one side is assigned a count of
    zero so that listens existing in only one database are also reported.
    """
    source_iter = iter(source_rows)
    target_iter = iter(target_rows)
    source_row = next(source_iter, None)
    target_row = next(target_iter, None)

    while source_row is not None or target_row is not None:
        if target_row is None or (source_row is not None and source_row[0] < target_row[0]):
            yield source_row[0], source_row[1], 0
            source_row = next(source_iter, None)
        elif source_row is None or target_row[0] < source_row[0]:
            yield target_row[0], 0, target_row[1]
            target_row = next(target_iter, None)
        else:
            yield source_row[0], source_row[1], target_row[1]
            source_row = next(source_iter, None)
            target_row = next(target_iter, None)


def _iter_window_user_counts(source_conn, target_conn, start, end, created_before, batch_size, window_number):
    """Stream merged per-user counts for one listened_at window from both databases."""
    params = (start, end, created_before)
    try:
        with source_conn.cursor(name=f"compare_listen_counts_source_{window_number}") as source_cur, \
                target_conn.cursor(name=f"compare_listen_counts_target_{window_number}") as target_cur:
            source_cur.itersize = batch_size
            target_cur.itersize = batch_size
            source_cur.execute(LISTEN_COUNTS_BY_USER_SQL, params)
            target_cur.execute(LISTEN_COUNTS_BY_USER_SQL, params)
            yield from _merge_user_counts(source_cur, target_cur)
    finally:
        # Named cursors hold a transaction open. End both snapshots after each window instead of
        # retaining long-running transactions for the duration of the full comparison.
        source_conn.rollback()
        target_conn.rollback()


def _comparison_range(source_conn, start, end):
    """ Resolve the listened_at range to compare, defaulting to the entire range of the source. """
    min_ts, max_ts = _fetch_one(source_conn, "SELECT min(listened_at), max(listened_at) FROM listen")
    if min_ts is None:
        raise click.ClickException("no listens found in the source, there is nothing to compare")
    start = start or min_ts
    end = end or (max_ts + timedelta(seconds=1))
    if start >= end:
        raise click.UsageError("--start must be earlier than --end")
    if start > min_ts or end <= max_ts:
        # a range narrower than the source silently leaves listens (and any spurious target rows)
        # outside it unchecked, say so instead of reporting a pass over part of the data
        current_app.logger.warning(
            "the compared range [%s, %s) does not cover every listen in the source ([%s, %s]), "
            "listens outside it are not compared in either database",
            start.isoformat(), end.isoformat(), min_ts.isoformat(), max_ts.isoformat()
        )
    return start, end


def compare_listen_counts(start, end, window, created_before, batch_size):
    """Compare per-user listen counts in TimescaleDB and the partitioned listens database."""
    if window <= timedelta(0):
        raise click.UsageError("comparison window must be greater than zero")

    logger = current_app.logger
    source_conn = connect_source()
    target_conn = connect_target()
    try:
        source_conn.set_session(readonly=True)
        target_conn.set_session(readonly=True)
        start, end = _comparison_range(source_conn, start, end)

        total_users = total_source_listens = total_target_listens = 0
        total_discrepancies = windows_checked = 0
        window_start = start
        overall_t0 = time.monotonic()

        while window_start < end:
            window_end = min(window_start + window, end)
            window_users = window_source_listens = window_target_listens = 0
            window_discrepancies = 0
            t0 = time.monotonic()

            for user_id, source_count, target_count in _iter_window_user_counts(
                    source_conn, target_conn, window_start, window_end, created_before,
                    batch_size, windows_checked):
                window_users += 1
                window_source_listens += source_count
                window_target_listens += target_count
                if source_count != target_count:
                    window_discrepancies += 1
                    # comparing a window that has not been copied yet mismatches on every user in
                    # it, log the first few and leave the rest to the counts below
                    if window_discrepancies <= MAX_LOGGED_DISCREPANCIES_PER_WINDOW:
                        logger.error(
                            "listen count mismatch: window [%s, %s), user_id=%d, "
                            "timescale=%d, listens=%d, delta=%+d",
                            window_start.isoformat(), window_end.isoformat(), user_id,
                            source_count, target_count, target_count - source_count,
                        )
                    elif window_discrepancies == MAX_LOGGED_DISCREPANCIES_PER_WINDOW + 1:
                        logger.error("more than %d users mismatch in window [%s, %s), logging only "
                                     "the count for the rest of it", MAX_LOGGED_DISCREPANCIES_PER_WINDOW,
                                     window_start.isoformat(), window_end.isoformat())

            windows_checked += 1
            total_users += window_users
            total_source_listens += window_source_listens
            total_target_listens += window_target_listens
            total_discrepancies += window_discrepancies
            logger.info(
                "checked window [%s, %s) at created < %s: %d users, "
                "%d TimescaleDB listens, %d listens DB listens, %d discrepancies (%.1fs)",
                window_start.isoformat(), window_end.isoformat(), created_before.isoformat(),
                window_users, window_source_listens, window_target_listens,
                window_discrepancies, time.monotonic() - t0,
            )
            window_start = window_end

        if not total_users:
            raise click.ClickException(
                f"listen count comparison compared nothing: no listens in "
                f"[{start.isoformat()}, {end.isoformat()}) with created < {created_before.isoformat()} "
                f"in either database, check --start / --end / --created-before"
            )
        if total_discrepancies:
            raise click.ClickException(
                f"listen count comparison failed: {total_discrepancies} user-window discrepancies "
                f"across {windows_checked} windows (TimescaleDB={total_source_listens}, "
                f"listens DB={total_target_listens})"
            )

        logger.info(
            "listen count comparison passed: %d user-window counts and %d listens matched "
            "across %d windows in [%s, %s) in %.1fs (created < %s)",
            total_users, total_source_listens, windows_checked, start.isoformat(), end.isoformat(),
            time.monotonic() - overall_t0, created_before.isoformat(),
        )
    finally:
        source_conn.close()
        target_conn.close()


batch_size_option = click.option("--batch-size", type=click.IntRange(min=1), default=DEFAULT_BATCH_SIZE,
                                 show_default=True, help="number of rows to fetch or write per batch")


@click.group()
def cli():
    """ Migrate listens from TimescaleDB to the user-partitioned PostgreSQL database.

    \b
    Initial copy checklist:
      1. create-schema
      2. full
      3. check-integrity
      4. create-indexes

    \b
    Catch-up cycle checklist:
      1. replay-deletes using the checkpoints logged by its previous run
      2. incremental using the previous created checkpoint minus a small overlap
      3. check-integrity

    \b
    For the final cycle, stop source writes and let the delete cron drain before running the
    catch-up cycle one last time.
    """


@cli.command(name="create-schema")
@click.option("--partitions", type=click.IntRange(min=1), default=PARTITION_COUNT, show_default=True,
              help="number of hash partitions of the listen table")
def create_schema_command(partitions):
    """ Create the user_id hash-partitioned listen table and its partitions. """
    with create_app().app_context():
        create_schema(partitions)


@cli.command(name="create-indexes")
def create_indexes_command():
    """ Create the indexes on the listen table, run after the initial full copy. """
    with create_app().app_context():
        create_indexes()


@cli.command(name="check-integrity")
def check_integrity_command():
    """ Verify target partitioning and check for duplicate logical listens. """
    with create_app().app_context():
        check_integrity()


@cli.command(name="compare-counts")
@batch_size_option
@click.option("--start", default=None,
              help="compare listens with listened_at >= this timestamp (ISO 8601), defaults to the oldest listen")
@click.option("--end", default=None,
              help="compare listens with listened_at < this timestamp (ISO 8601), defaults to just past the newest listen")
@click.option("--created-before", required=True,
              help="compare only rows with created < this fixed timestamp (ISO 8601)")
@click.option("--window-days", type=click.IntRange(min=1), default=DEFAULT_WINDOW.days, show_default=True,
              help="size of each listened_at window; 30 days aligns with the TimescaleDB chunk interval")
def compare_counts_command(batch_size, start, end, created_before, window_days):
    """Compare windowed per-user counts between TimescaleDB and the listens database.

    CREATED_BEFORE must be a stable cutoff before active writes: it hides rows inserted after it
    from both databases, but nothing hides a delete, so let the delete cron drain and replay its
    deletes first. A delete landing while the comparison runs is reported as a mismatch.

    --start / --end default to the full listened_at range of the source; narrowing them leaves
    every listen outside the range unchecked in both databases.

    A mismatch is logged with its user ID and listened_at window (at most 20 users per window) and
    makes the command exit unsuccessfully after the whole range has been checked. Comparing no
    listens at all is a failure too, not a pass.
    """
    with create_app().app_context():
        compare_listen_counts(
            _parse_ts(start), _parse_ts(end), timedelta(days=window_days),
            _parse_ts(created_before), batch_size,
        )


@cli.command(name="full")
@batch_size_option
@click.option("--start", default=None, help="only copy listens with listened_at >= this timestamp (ISO 8601)")
@click.option("--end", default=None, help="only copy listens with listened_at < this timestamp (ISO 8601)")
@click.option("--window-days", type=click.IntRange(min=1), default=DEFAULT_WINDOW.days, show_default=True,
              help="size of listened_at window read from timescale per iteration, each window is committed as a whole")
def full_command(batch_size, start, end, window_days):
    """ Copy all listens from timescale to the new listens database. """
    with create_app().app_context():
        migrate_full(_parse_ts(start), _parse_ts(end), timedelta(days=window_days), batch_size)


@cli.command(name="incremental")
@batch_size_option
@click.option("--since", required=True, help="copy listens with created >= this timestamp (ISO 8601)")
@click.option("--until", default=None, help="only copy listens with created < this timestamp (ISO 8601)")
def incremental_command(batch_size, since, until):
    """ Copy all listens created since the given timestamp. Idempotent. """
    with create_app().app_context():
        migrate_incremental(_parse_ts(since), _parse_ts(until), batch_size)


@cli.command(name="replay-deletes")
@batch_size_option
@click.option("--since-id", type=click.IntRange(min=0), default=0, show_default=True,
              help="replay listen_delete_metadata rows with id > this (value logged by the previous run)")
@click.option("--since-history-id", type=click.IntRange(min=0), default=0, show_default=True,
              help="replay deleted_user_listen_history rows with id > this (value logged by the previous run)")
def replay_deletes_command(batch_size, since_id, since_history_id):
    """ Replay listen / user deletes recorded in timescale against the new listens database. Idempotent. """
    with create_app().app_context():
        replay_deletes(since_id, since_history_id, batch_size)


if __name__ == "__main__":
    cli()
