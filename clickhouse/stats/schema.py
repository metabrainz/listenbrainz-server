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


CREATE_TABLES = [
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
    """
    CREATE TABLE IF NOT EXISTS artist_metadata (
        artist_id UInt64,
        artist_mbid String DEFAULT '',
        artist_name String DEFAULT '',
        country_code String DEFAULT '',
        updated_at DateTime64(3) DEFAULT now64(3)
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
        updated_at DateTime64(3) DEFAULT now64(3)
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
        updated_at DateTime64(3) DEFAULT now64(3)
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


def ensure_stats_schema(ch_client: Client) -> None:
    """Create the active stats schema if it does not already exist."""
    for statement in CREATE_FUNCTIONS.strip().split(";"):
        statement = statement.strip()
        if statement:
            ch_client.command(statement)

    for statement in CREATE_TABLES:
        ch_client.command(statement)

    for statement in CREATE_MATERIALIZED_VIEWS:
        ch_client.command(statement)
