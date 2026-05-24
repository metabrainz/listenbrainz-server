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
    CREATE TABLE IF NOT EXISTS raw_listens (
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
    ORDER BY (user_id, listened_at, recording_msid, raw_listen_id)
    SETTINGS index_granularity = 8192
    """,
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
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_raw_listens_to_submitted_artist_metadata
    TO artist_metadata
    AS
    SELECT
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
    GROUP BY artist_id, artist_mbid, artist_name
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_raw_listens_to_submitted_recording_metadata
    TO recording_metadata
    AS
    SELECT
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
    GROUP BY
        recording_id,
        recording_mbid,
        recording_name,
        artist_name,
        normalized_artist_credit_mbids,
        release_name,
        release_mbid
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_raw_listens_to_submitted_release_group_metadata
    TO release_group_metadata
    AS
    SELECT
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
    GROUP BY
        release_group_id,
        release_name,
        artist_name,
        normalized_artist_credit_mbids
    HAVING release_group_id != 0
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_raw_listens_to_listens
    TO listens
    AS
    SELECT
        expanded.listened_at,
        expanded.created,
        expanded.user_id,
        expanded.recording_msid,
        expanded.submitted_recording_id,
        expanded.recording_id,
        expanded.submitted_release_group_id,
        expanded.release_group_id,
        expanded.submitted_artist_ids,
        arrayMap(
            item -> tupleElement(item, 2),
            arraySort(
                item -> tupleElement(item, 1),
                groupArray(tuple(
                    expanded.artist_position,
                    if(
                        artist.artist_id > 0,
                        artist.artist_id,
                        submittedArtistId(expanded.artist_mbid, expanded.effective_artist_name)
                    )
                ))
            )
        ) AS artist_ids
    FROM (
        SELECT
            with_release.*,
            artist_position,
            artist_mbid
        FROM (
            SELECT
                base.raw_listen_id,
                base.listened_at,
                base.created,
                base.user_id,
                base.recording_msid,
                base.submitted_recording_id,
                if(base.matched_recording_id > 0, base.matched_recording_id, base.submitted_recording_id) AS recording_id,
                base.submitted_release_group_id,
                if(release.release_group_id > 0, release.release_group_id, base.submitted_release_group_id) AS release_group_id,
                base.submitted_artist_ids,
                base.effective_artist_name,
                base.effective_artist_mbids
            FROM (
                SELECT
                    r.raw_listen_id,
                    r.listened_at,
                    r.created,
                    r.user_id,
                    r.recording_msid,
                    r.artist_name,
                    r.release_mbid,
                    submittedRecordingId(r.recording_mbid, r.artist_name, r.recording_name) AS submitted_recording_id,
                    submittedReleaseGroupId('', r.artist_name, r.release_name) AS submitted_release_group_id,
                    arrayMap(
                        mbid -> submittedArtistId(mbid, r.artist_name),
                        if(empty(r.artist_credit_mbids), [''], r.artist_credit_mbids)
                    ) AS submitted_artist_ids,
                    recording.recording_id AS matched_recording_id,
                    if(recording.artist_name != '', recording.artist_name, r.artist_name) AS effective_artist_name,
                    if(
                        empty(recording.artist_credit_mbids),
                        if(empty(r.artist_credit_mbids), [''], r.artist_credit_mbids),
                        recording.artist_credit_mbids
                    ) AS effective_artist_mbids,
                    if(recording.release_mbid != '', recording.release_mbid, r.release_mbid) AS effective_release_mbid
                FROM raw_listens AS r
                ANY LEFT JOIN (
                    SELECT
                        recording_mbid,
                        argMin(recording_id, if(recording_id > 0 AND recording_id <= 4294967295, 0, 1)) AS recording_id,
                        argMin(artist_name, if(recording_id > 0 AND recording_id <= 4294967295, 0, 1)) AS artist_name,
                        argMin(artist_credit_mbids, if(recording_id > 0 AND recording_id <= 4294967295, 0, 1)) AS artist_credit_mbids,
                        argMin(release_mbid, if(recording_id > 0 AND recording_id <= 4294967295, 0, 1)) AS release_mbid
                    FROM recording_metadata
                    WHERE recording_mbid != ''
                    GROUP BY recording_mbid
                ) AS recording
                    ON r.recording_mbid = recording.recording_mbid
            ) AS base
            ANY LEFT JOIN (
                SELECT
                    release_mbid,
                    argMin(release_group_id, if(release_group_id > 0 AND release_group_id <= 4294967295, 0, 1)) AS release_group_id
                FROM release_metadata
                WHERE release_mbid != ''
                GROUP BY release_mbid
            ) AS release
                ON base.effective_release_mbid = release.release_mbid
        ) AS with_release
        ARRAY JOIN
            arrayEnumerate(effective_artist_mbids) AS artist_position,
            effective_artist_mbids AS artist_mbid
    ) AS expanded
    ANY LEFT JOIN (
        SELECT
            artist_mbid,
            argMin(artist_id, if(artist_id > 0 AND artist_id <= 4294967295, 0, 1)) AS artist_id
        FROM artist_metadata
        WHERE artist_mbid != ''
        GROUP BY artist_mbid
    ) AS artist
        ON expanded.artist_mbid = artist.artist_mbid
    GROUP BY
        expanded.raw_listen_id,
        expanded.listened_at,
        expanded.created,
        expanded.user_id,
        expanded.recording_msid,
        expanded.submitted_recording_id,
        expanded.recording_id,
        expanded.submitted_release_group_id,
        expanded.release_group_id,
        expanded.submitted_artist_ids
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
