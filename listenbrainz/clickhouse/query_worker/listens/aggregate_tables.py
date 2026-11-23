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

LISTEN_AGGREGATES = (HOURLY_COUNTS,)
