"""ClickHouse schema for the active stats pipeline."""

from clickhouse_connect.driver import Client


CREATE_FUNCTIONS = """
CREATE OR REPLACE FUNCTION submittedArtistId AS (mbid, name) ->
    sipHash64(concat('artist|mbid:', ifNull(mbid, ''), '|name:', lowerUTF8(ifNull(name, ''))));

CREATE OR REPLACE FUNCTION submittedRecordingId AS (recording_mbid, artist_name, recording_name) ->
    if(
        recording_mbid IS NOT NULL AND recording_mbid != '',
        sipHash64(concat('recording|mbid:', recording_mbid)),
        sipHash64(concat(
            'recording|artist:', lowerUTF8(ifNull(artist_name, '')),
            '|name:', lowerUTF8(ifNull(recording_name, ''))
        ))
    );

CREATE OR REPLACE FUNCTION submittedReleaseGroupId AS (release_group_mbid, artist_name, release_name) ->
    if(
        release_group_mbid IS NOT NULL AND release_group_mbid != '',
        sipHash64(concat('release_group|mbid:', release_group_mbid)),
        if(
            release_name IS NOT NULL AND release_name != '',
            sipHash64(concat(
                'release_group|artist:', lowerUTF8(ifNull(artist_name, '')),
                '|name:', lowerUTF8(ifNull(release_name, ''))
            )),
            toUInt64(0)
        )
    );
"""


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
        recording_msid String,
        artist_name String DEFAULT '',
        release_name String DEFAULT '',
        release_mbid String DEFAULT '',
        recording_name String DEFAULT '',
        recording_mbid String DEFAULT '',
        artist_credit_mbids Array(String) DEFAULT []
    ) ENGINE = MergeTree()
    PARTITION BY load_id
    ORDER BY (user_id, listened_at, recording_msid, raw_listen_id)
    SETTINGS index_granularity = 8192
"""

CREATE_TABLES = [
    CREATE_RAW_LISTENS_TABLE,
    """
    CREATE TABLE IF NOT EXISTS listens (
        listened_at DateTime64(3),
        created DateTime64(3) DEFAULT now64(3),
        user_id UInt32,
        recording_msid String,
        submitted_recording_id UInt64,
        recording_id UInt64,
        submitted_release_group_id UInt64 DEFAULT 0,
        release_group_id UInt64 DEFAULT 0,
        submitted_artist_ids Array(UInt64) DEFAULT [],
        artist_ids Array(UInt64) DEFAULT []
    ) ENGINE = MergeTree()
    ORDER BY (user_id, listened_at, recording_msid)
    SETTINGS index_granularity = 8192
    """,
    # Metadata tables are ORDER BY <numeric id>, but dump ingestion joins them by *_mbid
    # (see PROCESS_RAW_LISTENS_BATCH). Without these bloom filters the IN-subquery probe
    # does a full table scan; with them ~97% of granules are pruned per batch.
    """
    CREATE TABLE IF NOT EXISTS artist_metadata (
        artist_id UInt64,
        artist_mbid String DEFAULT '',
        artist_name String DEFAULT '',
        country_code String DEFAULT '',
        updated_at DateTime64(3) DEFAULT now64(3),
        INDEX idx_artist_mbid artist_mbid TYPE bloom_filter(0.01) GRANULARITY 4
    ) ENGINE = ReplacingMergeTree(updated_at)
    ORDER BY artist_id
    """,
    """
    CREATE TABLE IF NOT EXISTS recording_metadata (
        recording_id UInt64,
        recording_mbid String DEFAULT '',
        recording_name String DEFAULT '',
        artist_name String DEFAULT '',
        artist_credit_mbids Array(String) DEFAULT [],
        release_name String DEFAULT '',
        release_mbid String DEFAULT '',
        artists String DEFAULT '',
        caa_id UInt64 DEFAULT 0,
        caa_release_mbid String DEFAULT '',
        updated_at DateTime64(3) DEFAULT now64(3),
        INDEX idx_recording_mbid recording_mbid TYPE bloom_filter(0.01) GRANULARITY 4
    ) ENGINE = ReplacingMergeTree(updated_at)
    ORDER BY recording_id
    """,
    """
    CREATE TABLE IF NOT EXISTS release_metadata (
        release_id UInt64,
        release_mbid String DEFAULT '',
        release_group_id UInt64 DEFAULT 0,
        release_group_mbid String DEFAULT '',
        release_name String DEFAULT '',
        album_artist_name String DEFAULT '',
        first_release_date_year UInt16 DEFAULT 0,
        caa_id UInt64 DEFAULT 0,
        caa_release_mbid String DEFAULT '',
        artist_credit_mbids Array(String) DEFAULT [],
        artists String DEFAULT '',
        updated_at DateTime64(3) DEFAULT now64(3),
        INDEX idx_release_mbid release_mbid TYPE bloom_filter(0.01) GRANULARITY 4
    ) ENGINE = ReplacingMergeTree(updated_at)
    ORDER BY release_id
    """,
    """
    CREATE TABLE IF NOT EXISTS release_group_metadata (
        release_group_id UInt64,
        release_group_mbid String DEFAULT '',
        release_group_name String DEFAULT '',
        artist_name String DEFAULT '',
        artist_credit_mbids Array(String) DEFAULT [],
        artists String DEFAULT '',
        caa_id UInt64 DEFAULT 0,
        caa_release_mbid String DEFAULT '',
        first_release_date_year UInt16 DEFAULT 0,
        primary_type String DEFAULT '',
        updated_at DateTime64(3) DEFAULT now64(3)
    ) ENGINE = ReplacingMergeTree(updated_at)
    ORDER BY release_group_id
    """,
    """
    CREATE TABLE IF NOT EXISTS user_artist_stats_daily (
        date Date,
        user_id UInt32,
        artist_id UInt64,
        listen_count SimpleAggregateFunction(sum, Int64)
    ) ENGINE = AggregatingMergeTree()
    ORDER BY (date, user_id, artist_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS user_recording_stats_daily (
        date Date,
        user_id UInt32,
        recording_id UInt64,
        listen_count SimpleAggregateFunction(sum, Int64)
    ) ENGINE = AggregatingMergeTree()
    ORDER BY (date, user_id, recording_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS user_release_group_stats_daily (
        date Date,
        user_id UInt32,
        release_group_id UInt64,
        listen_count SimpleAggregateFunction(sum, Int64)
    ) ENGINE = AggregatingMergeTree()
    ORDER BY (date, user_id, release_group_id)
    """,
    # Listens deleted in LB after they were dumped (listen_delete_metadata) and users whose
    # listen history was deleted (deleted_user_listen_history), imported from timescale.
    # Kept permanently: they are applied retroactively to listens / daily stats when
    # imported and used to filter dump loads, since a dump created before the deletion
    # still contains the listen.
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

CREATE_MATERIALIZED_VIEWS = [
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_raw_listens_to_submitted_artist_metadata
    TO artist_metadata
    AS
    SELECT DISTINCT
        artist_id,
        artist_mbid,
        artist_name,
        '' AS country_code
    FROM (
        SELECT
            submittedArtistId(artist_mbid, artist_name) AS artist_id,
            artist_mbid,
            artist_name
        FROM raw_listens
        ARRAY JOIN if(empty(artist_credit_mbids), [''], artist_credit_mbids) AS artist_mbid
    ) AS normalized_artists
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_raw_listens_to_submitted_recording_metadata
    TO recording_metadata
    AS
    SELECT DISTINCT
        recording_id,
        recording_mbid,
        recording_name,
        artist_name,
        normalized_artist_credit_mbids AS artist_credit_mbids,
        release_name,
        release_mbid,
        '' AS artists,
        toUInt64(0) AS caa_id,
        '' AS caa_release_mbid
    FROM (
        SELECT
            submittedRecordingId(recording_mbid, artist_name, recording_name) AS recording_id,
            recording_mbid,
            recording_name,
            artist_name,
            if(empty(artist_credit_mbids), [''], artist_credit_mbids) AS normalized_artist_credit_mbids,
            release_name,
            release_mbid
        FROM raw_listens
    ) AS normalized_recordings
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_raw_listens_to_submitted_release_group_metadata
    TO release_group_metadata
    AS
    SELECT DISTINCT
        release_group_id,
        '' AS release_group_mbid,
        release_name AS release_group_name,
        artist_name,
        normalized_artist_credit_mbids AS artist_credit_mbids,
        '' AS artists,
        toUInt64(0) AS caa_id,
        '' AS caa_release_mbid,
        toUInt16(0) AS first_release_date_year,
        '' AS primary_type
    FROM (
        SELECT
            submittedReleaseGroupId('', artist_name, release_name) AS release_group_id,
            release_name,
            artist_name,
            if(empty(artist_credit_mbids), [''], artist_credit_mbids) AS normalized_artist_credit_mbids
        FROM raw_listens
    ) AS normalized_release_groups
    WHERE release_group_id != 0
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_listens_to_artist_stats
    TO user_artist_stats_daily
    AS
    SELECT
        toDate(listened_at) AS date,
        user_id,
        arrayJoin(artist_ids) AS artist_id,
        toInt64(1) AS listen_count
    FROM listens
    WHERE notEmpty(artist_ids)
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_listens_to_recording_stats
    TO user_recording_stats_daily
    AS
    SELECT
        toDate(listened_at) AS date,
        user_id,
        recording_id,
        toInt64(1) AS listen_count
    FROM listens
    WHERE recording_id != 0
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_listens_to_release_group_stats
    TO user_release_group_stats_daily
    AS
    SELECT
        toDate(listened_at) AS date,
        user_id,
        release_group_id,
        toInt64(1) AS listen_count
    FROM listens
    WHERE release_group_id != 0
    """,
]

MATERIALIZED_VIEW_NAMES = [
    "mv_raw_listens_to_submitted_artist_metadata",
    "mv_raw_listens_to_submitted_recording_metadata",
    "mv_raw_listens_to_submitted_release_group_metadata",
    "mv_listens_to_artist_stats",
    "mv_listens_to_recording_stats",
    "mv_listens_to_release_group_stats",
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
    # the views selecting from raw_listens are recreated by ensure_stats_schema right after
    for view_name in MATERIALIZED_VIEW_NAMES:
        if view_name.startswith("mv_raw_listens_"):
            ch_client.command(f"DROP TABLE IF EXISTS {view_name}")
    ch_client.command("DROP TABLE raw_listens")
    ch_client.command(CREATE_RAW_LISTENS_TABLE)


def ensure_stats_schema(ch_client: Client, recreate_views: bool = False) -> None:
    """Create the active stats schema if it does not already exist.

    Safe to call from every job: all statements are idempotent and nothing is
    dropped, so concurrent inserts keep flowing through the materialized views.

    Args:
        recreate_views: drop and recreate the materialized views. Only needed after
            a view definition changes; do this while no dump load / metadata refresh
            is running, since rows inserted while a view is missing are not
            aggregated into its target table.
    """
    for statement in CREATE_FUNCTIONS.strip().split(";"):
        statement = statement.strip()
        if statement:
            ch_client.command(statement)

    for statement in CREATE_TABLES:
        ch_client.command(statement)
    _ensure_raw_listens_partitioned_by_load(ch_client)

    if recreate_views:
        for view_name in MATERIALIZED_VIEW_NAMES:
            ch_client.command(f"DROP TABLE IF EXISTS {view_name}")

    for statement in CREATE_MATERIALIZED_VIEWS:
        ch_client.command(statement)
