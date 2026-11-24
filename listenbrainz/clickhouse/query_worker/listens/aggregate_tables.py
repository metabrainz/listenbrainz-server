"""ClickHouse tables maintained from signed listen changes."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ListenAggregate:
    name: str
    source_columns: tuple[str, ...]
    columns: str
    engine: str
    select: str  # SELECT from {source}, with delta = +1 for an insert and -1 for a deletion.


HOURLY_COUNTS = ListenAggregate(
    name="hourly_listen_counts",
    source_columns=("user_id", "listened_at"),
    columns="user_id UInt32, day Date, hour UInt8, listen_count Int64",
    engine="SummingMergeTree PARTITION BY toYear(day) ORDER BY (user_id, day, hour)",
    select="""
        SELECT user_id, toDate(listened_at, 'UTC') AS day, toHour(listened_at, 'UTC') AS hour,
               sum(delta) AS listen_count
          FROM {source}
         GROUP BY user_id, day, hour
    """,
)

# Both views must resolve an incoming credit to the same integer ID.
ARTIST_SOURCE_COLUMNS = ("user_id", "listened_at", "artist_credit_mbids", "artist_name")
RESOLVED_ARTISTS = """
    WITH credits AS (
        SELECT user_id, listened_at, delta, artist_name,
               arrayJoin(emptyArrayToSingle(arrayMap(x -> toString(x), artist_credit_mbids))) AS artist_mbid
          FROM {source}
    ), resolved AS (
        SELECT user_id, listened_at, delta, artist_mbid,
               if(isNull(mb_artist_id),
                  bitOr(reinterpretAsUInt128(sipHash128(artist_mbid, lowerUTF8(artist_name))),
                        bitShiftLeft(toUInt128(1), 127)),
                  toUInt128(assumeNotNull(mb_artist_id))) AS artist_id,
               coalesce(canonical_name, artist_name) AS display_name
          FROM credits ANY LEFT JOIN {artist_lookup} ON artist_mbid = mbid
    )
"""

DAILY_ARTIST_COUNTS = ListenAggregate(
    name="user_artist_stats_daily",
    source_columns=ARTIST_SOURCE_COLUMNS,
    columns="user_id UInt32, day Date, artist_id UInt128, listen_count Int64",
    engine="SummingMergeTree PARTITION BY toYear(day) ORDER BY (user_id, day, artist_id)",
    select=RESOLVED_ARTISTS + """
        SELECT user_id, toDate(listened_at, 'UTC') AS day, artist_id, sum(delta) AS listen_count
          FROM resolved
         GROUP BY user_id, day, artist_id
    """,
)

ARTIST_METADATA = ListenAggregate(
    name="artist_metadata",
    source_columns=ARTIST_SOURCE_COLUMNS,
    columns="""artist_id UInt128, artist_mbid SimpleAggregateFunction(min, String),
               display_name SimpleAggregateFunction(min, String)""",
    engine="AggregatingMergeTree ORDER BY artist_id",
    select=RESOLVED_ARTISTS + """
        SELECT artist_id, min(artist_mbid) AS artist_mbid, min(display_name) AS display_name
          FROM resolved
         WHERE delta > 0
         GROUP BY artist_id
    """,
)

LISTEN_AGGREGATES = (HOURLY_COUNTS, DAILY_ARTIST_COUNTS, ARTIST_METADATA)
