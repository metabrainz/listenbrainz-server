"""ClickHouse schema of the stats pipeline."""

from clickhouse_connect.driver import Client


CREATE_TABLES = [
    # Staging table: each load uses its own load_id partition, dropped once processed.
    """
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
    """,
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
        to_ts Int64,
        version UInt64 DEFAULT toUnixTimestamp64Milli(now64(3))
    ) ENGINE = ReplacingMergeTree(version)
    ORDER BY (stat_type, time_range)
    """,
]

def ensure_stats_schema(ch_client: Client) -> None:
    """Create the stats schema; idempotent, so safe to call from every job."""
    for statement in CREATE_TABLES:
        ch_client.command(statement)
