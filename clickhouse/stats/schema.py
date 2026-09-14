"""ClickHouse schema for the active stats pipeline."""

from clickhouse_connect.driver import Client


# raw_listens is a staging table: each dump load inserts under its own load_id partition,
# processes only that partition into listens and drops the partition afterwards, so a
# load never re-processes rows from earlier loads and a failed load can be retried by
# dropping its partition.
CREATE_RAW_LISTENS_TABLE = """
    CREATE TABLE IF NOT EXISTS raw_listens (
        load_id String,
        raw_listen_id UUID DEFAULT generateUUIDv4(),
        listened_at DateTime64(3),
        created DateTime64(3) DEFAULT now64(3),
        user_id UInt32,
        recording_msid String
    ) ENGINE = MergeTree()
    PARTITION BY load_id
    ORDER BY (user_id, listened_at, recording_msid, raw_listen_id)
    SETTINGS index_granularity = 8192
"""

CREATE_TABLES = [
    CREATE_RAW_LISTENS_TABLE,
    # One row per listen. Only what the activity stats and the deletion / dedup logic
    # need: who listened when, plus the recording_msid that (with user_id and
    # listened_at) identifies a listen in ListenBrainz.
    """
    CREATE TABLE IF NOT EXISTS listens (
        listened_at DateTime64(3),
        created DateTime64(3) DEFAULT now64(3),
        user_id UInt32,
        recording_msid String
    ) ENGINE = MergeTree()
    ORDER BY (user_id, listened_at, recording_msid)
    SETTINGS index_granularity = 8192
    """,
    # Listens deleted in LB after they were dumped (listen_delete_metadata) and users whose
    # listen history was deleted (deleted_user_listen_history), imported from timescale.
    # Kept permanently: they are applied retroactively to listens when imported and used
    # to filter dump loads, since a dump created before the deletion still contains the
    # listen.
    """
    CREATE TABLE IF NOT EXISTS deleted_listens (
        id UInt64,
        user_id UInt32,
        listened_at DateTime64(3),
        recording_msid String,
        created DateTime64(3)
    ) ENGINE = ReplacingMergeTree()
    ORDER BY (user_id, listened_at, recording_msid, id)
    """,
    """
    CREATE TABLE IF NOT EXISTS deleted_user_listen_history (
        id UInt64,
        user_id UInt32,
        max_created DateTime64(3)
    ) ENGINE = ReplacingMergeTree()
    ORDER BY (user_id, id)
    """,
    # One row per listens dump loaded into `listens`, mirroring the import metadata the
    # Spark pipeline keeps in HDFS. An incremental catch-up import consults this to work
    # out which of the dumps on the FTP server it still has to load; a replacing full
    # dump load supersedes every incremental imported before it, so rows are kept
    # forever and filtered by `imported_at` rather than deleted.
    """
    CREATE TABLE IF NOT EXISTS imported_dumps (
        dump_id UInt64,
        dump_type LowCardinality(String),
        imported_at DateTime64(3) DEFAULT now64(3)
    ) ENGINE = ReplacingMergeTree(imported_at)
    ORDER BY (dump_type, dump_id)
    """,
    # High-water marks for incremental imports from external sources (e.g. last
    # listen_delete_metadata.id applied), so re-running an import is idempotent.
    """
    CREATE TABLE IF NOT EXISTS import_state (
        name LowCardinality(String),
        last_id UInt64,
        version UInt64 DEFAULT toUnixTimestamp64Milli(now64(3))
    ) ENGINE = ReplacingMergeTree(version)
    ORDER BY name
    """,
    # Per-user cache state: when each user's stats were last computed for each time_range
    # (max(created) of listens at that time), used to find users needing an update.
    """
    CREATE TABLE IF NOT EXISTS user_stats_cache_state (
        user_id UInt32,
        stat_type String,
        time_range String,
        last_computed_created DateTime64(3),
        updated_at DateTime64(3) DEFAULT now64(3)
    ) ENGINE = ReplacingMergeTree(updated_at)
    ORDER BY (user_id, stat_type, time_range)
    """,
    """
    CREATE TABLE IF NOT EXISTS stats_cache_state (
        stat_type LowCardinality(String),
        time_range LowCardinality(String),
        last_computed DateTime64(3),
        period_start Date,
        version UInt64 DEFAULT toUnixTimestamp64Milli(now64(3))
    ) ENGINE = ReplacingMergeTree(version)
    ORDER BY (stat_type, time_range)
    """,
]

# Objects of the retired entity (artist / recording / release group) stats. The
# materialized views are dropped on every schema check: left in place they would keep
# feeding the orphaned metadata and daily stats tables from every load. The tables
# themselves hold data and are left for an operator to drop
# (DROP TABLE {artist,recording,release,release_group}_metadata,
# user_{artist,recording,release_group}_stats_daily), as are the extra entity id
# columns an older `listens` / `raw_listens` table still carries.
OBSOLETE_MATERIALIZED_VIEWS = [
    "mv_raw_listens_to_submitted_artist_metadata",
    "mv_raw_listens_to_submitted_recording_metadata",
    "mv_raw_listens_to_submitted_release_group_metadata",
    "mv_listens_to_artist_stats",
    "mv_listens_to_recording_stats",
    "mv_listens_to_release_group_stats",
]

OBSOLETE_FUNCTIONS = [
    "submittedArtistId",
    "submittedRecordingId",
    "submittedReleaseGroupId",
]


def _ensure_raw_listens_partitioned_by_load(ch_client: Client) -> None:
    """Recreate a pre-load_id raw_listens staging table (only if it is empty).

    raw_listens used to be unpartitioned. CREATE TABLE IF NOT EXISTS leaves such a table
    alone, and a partition key cannot be added to an existing table, so drop and recreate
    it. Refuse if it still holds rows: they belong to a load whose processing state is
    unknown, so an operator must truncate it (or finish that load) first.
    """
    result = ch_client.query(
        "SELECT partition_key FROM system.tables WHERE database = currentDatabase() AND name = 'raw_listens'"
    )
    if not result.result_rows or "load_id" in result.result_rows[0][0]:
        return
    row_count = ch_client.query("SELECT count() FROM raw_listens").first_row[0]
    if row_count:
        raise RuntimeError(
            f"raw_listens is not partitioned by load_id but still holds {row_count} rows; "
            "TRUNCATE TABLE raw_listens (after making sure no load is in progress) and rerun init_schema"
        )
    ch_client.command("DROP TABLE raw_listens")
    ch_client.command(CREATE_RAW_LISTENS_TABLE)


def _drop_obsolete_objects(ch_client: Client) -> None:
    """Drop the materialized views and functions of the retired entity stats."""
    for view_name in OBSOLETE_MATERIALIZED_VIEWS:
        ch_client.command(f"DROP TABLE IF EXISTS {view_name}")
    for function_name in OBSOLETE_FUNCTIONS:
        ch_client.command(f"DROP FUNCTION IF EXISTS {function_name}")


def ensure_stats_schema(ch_client: Client) -> None:
    """Create the active stats schema if it does not already exist.

    Safe to call from every job: all statements are idempotent and no data-holding
    table is dropped, so concurrent inserts keep flowing.
    """
    # views must go before raw_listens is recreated, since they select from it
    _drop_obsolete_objects(ch_client)

    for statement in CREATE_TABLES:
        ch_client.command(statement)
    _ensure_raw_listens_partitioned_by_load(ch_client)
