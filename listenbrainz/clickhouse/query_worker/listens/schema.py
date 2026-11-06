"""ClickHouse schema of the listens and their import state."""

from clickhouse_connect.driver import Client

# The columns of a listen, as in the Spark listen dumps (SPARK_LISTENS_SCHEMA).
LISTEN_COLUMNS = """
        listened_at DateTime64(3),
        created DateTime64(3) DEFAULT now64(3),
        user_id UInt32,
        recording_msid UUID,
        artist_name String,
        artist_credit_id Nullable(Int64),
        release_name Nullable(String),
        release_mbid Nullable(UUID),
        recording_name String,
        recording_mbid Nullable(UUID),
        artist_credit_mbids Array(UUID)
"""

LISTEN_COLUMN_NAMES = [
    "listened_at", "created", "user_id", "recording_msid", "artist_name", "artist_credit_id",
    "release_name", "release_mbid", "recording_name", "recording_mbid", "artist_credit_mbids",
]

# One row per listen; (user_id, listened_at, recording_msid) identifies it in LB.
LISTENS_TABLE = f"""
    CREATE TABLE {{if_not_exists}} {{name}} (
        {LISTEN_COLUMNS}
    ) ENGINE = MergeTree()
    ORDER BY (user_id, listened_at, recording_msid)
    SETTINGS index_granularity = 8192
"""

CREATE_TABLES = [
    LISTENS_TABLE.format(if_not_exists="IF NOT EXISTS", name="listens"),
    # High-water marks of incremental imports (see import_state.py).
    """
    CREATE TABLE IF NOT EXISTS import_state (
        name LowCardinality(String),
        last_id UInt64,
        version UInt64
    ) ENGINE = ReplacingMergeTree(version)
    ORDER BY name
    """,
]


def create_listens_table(ch_client: Client, name: str) -> None:
    """Create an empty table with the schema of listens (not that of an existing listens)."""
    ch_client.command(LISTENS_TABLE.format(if_not_exists="", name=name))


def ensure_schema(ch_client: Client) -> None:
    """Create the schema; idempotent, so safe to call from every job."""
    for statement in CREATE_TABLES:
        ch_client.command(statement)
