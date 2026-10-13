"""ClickHouse schema for the active stats pipeline."""

from clickhouse_connect.driver import Client

from clickhouse.stats.import_state import INCREMENTAL_DUMP_STATE, get_import_state


# Staging table: each load uses its own load_id partition, dropped once processed.
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
    # One row per listen; (user_id, listened_at, recording_msid) identifies it in LB.
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
    # Deletions imported from LB, kept to filter dump loads made before the deletion.
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
    # High-water marks of incremental imports (see import_state.py).
    """
    CREATE TABLE IF NOT EXISTS import_state (
        name LowCardinality(String),
        last_id UInt64,
        version UInt64 DEFAULT toUnixTimestamp64Milli(now64(3))
    ) ENGINE = ReplacingMergeTree(version)
    ORDER BY name
    """,
    # When each user's stats were last computed per time range (max(created) at the time).
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
    # The period and range end (to_ts) each time range was last computed for.
    """
    CREATE TABLE IF NOT EXISTS stats_cache_state (
        stat_type LowCardinality(String),
        time_range LowCardinality(String),
        last_computed DateTime64(3),
        period_start Date,
        to_ts Int64 DEFAULT 0,
        version UInt64 DEFAULT toUnixTimestamp64Milli(now64(3))
    ) ENGINE = ReplacingMergeTree(version)
    ORDER BY (stat_type, time_range)
    """,
]

# Columns added to existing tables after they were first created.
ADD_COLUMNS = [
    "ALTER TABLE stats_cache_state ADD COLUMN IF NOT EXISTS to_ts Int64 DEFAULT 0 AFTER period_start",
]

# Objects of the retired entity stats. The views would keep feeding orphaned tables, so
# they are dropped; the tables (*_metadata, user_*_stats_daily) are left to an operator.
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
    """Recreate an old, unpartitioned raw_listens; refuses if it still holds rows."""
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


# The incremental dump mark used to be derived from imported_dumps, a row per loaded
# dump: the latest full dump, or a newer incremental imported after it. The table is
# left for an operator to drop.
SEED_INCREMENTAL_DUMP_STATE = f"""
    INSERT INTO import_state (name, last_id)
    SELECT '{INCREMENTAL_DUMP_STATE}', last_id
    FROM (
        SELECT greatest(
            (SELECT argMax(dump_id, imported_at) FROM imported_dumps FINAL WHERE dump_type = 'full'),
            (SELECT max(dump_id) FROM imported_dumps FINAL
              WHERE dump_type = 'incremental'
                AND imported_at >= (SELECT max(imported_at) FROM imported_dumps FINAL WHERE dump_type = 'full'))
        ) AS last_id
    )
    WHERE last_id > 0
"""


def _seed_incremental_dump_state(ch_client: Client) -> None:
    """Seed the incremental dump mark from the old imported_dumps table, once."""
    if not ch_client.command("EXISTS TABLE imported_dumps"):
        return
    if get_import_state(ch_client, INCREMENTAL_DUMP_STATE):
        return
    ch_client.command(SEED_INCREMENTAL_DUMP_STATE)


def _drop_obsolete_objects(ch_client: Client) -> None:
    """Drop the materialized views and functions of the retired entity stats."""
    for view_name in OBSOLETE_MATERIALIZED_VIEWS:
        ch_client.command(f"DROP TABLE IF EXISTS {view_name}")
    for function_name in OBSOLETE_FUNCTIONS:
        ch_client.command(f"DROP FUNCTION IF EXISTS {function_name}")


def ensure_stats_schema(ch_client: Client) -> None:
    """Create the stats schema; idempotent, so safe to call from every job."""
    # views must go before raw_listens is recreated, since they select from it
    _drop_obsolete_objects(ch_client)

    for statement in CREATE_TABLES:
        ch_client.command(statement)
    for statement in ADD_COLUMNS:
        ch_client.command(statement)
    _ensure_raw_listens_partitioned_by_load(ch_client)
    _seed_incremental_dump_state(ch_client)
