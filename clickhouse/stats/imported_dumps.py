"""Track which listens dumps have been loaded into ClickHouse.

The FTP server keeps every incremental dump, but a load only ever pulls the dumps
it is told to. Without a record of what has already been loaded, a missed cron run
leaves a permanent hole in ``listens``: the next run fetches the newest dump again
and the skipped days are never fetched at all.

``imported_dumps`` is that record, mirroring the import metadata the Spark pipeline
keeps in HDFS (see listenbrainz_spark/listens/dump.py). A replacing full dump load
truncates ``listens``, so incrementals loaded before it no longer contribute any
rows; rather than deleting those rows, the catch-up only counts incrementals
imported at or after the latest full dump.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from clickhouse_connect.driver import Client

from clickhouse.stats.ftp import DumpType

logger = logging.getLogger(__name__)


# imported_at is bound as a string and parsed by ClickHouse: a DateTime64(3) parameter
# is truncated to whole seconds by the driver, which would reorder rows recorded within
# the same second of each other.
RECORD_IMPORTED_DUMP_AT = """
    INSERT INTO imported_dumps (dump_id, dump_type, imported_at)
    SELECT {dump_id:UInt64}, {dump_type:String}, parseDateTime64BestEffort({imported_at:String}, 3)
"""


def record_imported_dump(
    ch_client: Client, dump_id: int, dump_type: DumpType, imported_at: datetime = None
) -> None:
    """Record that ``dump_id`` has been loaded into listens.

    Args:
        imported_at: when the dump landed in listens, as naive UTC; defaults to now.
            Pass it to backfill a dump that was loaded before this table existed --
            the catch-up compares it against the latest full dump import, so a dump
            loaded before that full dump has to carry its real timestamp.
    """
    if imported_at is None:
        ch_client.command(
            "INSERT INTO imported_dumps (dump_id, dump_type) VALUES ({dump_id:UInt64}, {dump_type:String})",
            parameters={"dump_id": dump_id, "dump_type": dump_type.value},
        )
        return

    if imported_at.tzinfo is not None:
        imported_at = imported_at.astimezone(timezone.utc).replace(tzinfo=None)
    ch_client.command(
        RECORD_IMPORTED_DUMP_AT,
        parameters={
            "dump_id": dump_id,
            "dump_type": dump_type.value,
            "imported_at": imported_at.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        },
    )


def get_latest_full_dump(ch_client: Client) -> Optional[dict]:
    """Return the most recently imported full dump, or None if there is none."""
    result = ch_client.query(
        """
        SELECT dump_id, imported_at
          FROM imported_dumps FINAL
         WHERE dump_type = {dump_type:String}
      ORDER BY imported_at DESC, dump_id DESC
         LIMIT 1
        """,
        parameters={"dump_type": DumpType.FULL.value},
    )
    if not result.result_rows:
        return None
    dump_id, imported_at = result.first_row
    return {"dump_id": dump_id, "imported_at": imported_at}


# The cutoff is compared inside ClickHouse rather than passed back in as a parameter:
# a DateTime64(3) bound round-tripped through the driver loses its milliseconds, which
# would let an incremental imported in the same second as the full dump slip through.
# With no full dump imported the subquery yields the epoch, so every incremental counts.
INCREMENTAL_DUMPS_SINCE_LATEST_FULL = """
    SELECT dump_id
      FROM imported_dumps FINAL
     WHERE dump_type = {dump_type:String}
       AND imported_at >= (
             SELECT max(imported_at)
               FROM imported_dumps FINAL
              WHERE dump_type = {full_dump_type:String}
           )
"""


def get_incremental_dumps_since_latest_full(ch_client: Client) -> set[int]:
    """Return the ids of the incremental dumps imported since the latest full dump.

    Incrementals imported before the latest full dump are excluded: that full dump load
    truncated listens, so their rows are gone and they have to be loaded again.
    """
    result = ch_client.query(
        INCREMENTAL_DUMPS_SINCE_LATEST_FULL,
        parameters={
            "dump_type": DumpType.INCREMENTAL.value,
            "full_dump_type": DumpType.FULL.value,
        },
    )
    return {row[0] for row in result.result_rows}


def select_missing_incremental_dumps(
    available: list[tuple[int, str]],
    imported_ids: set[int],
    after_dump_id: int = None,
) -> list[tuple[int, str]]:
    """Pick the incremental dumps still to be loaded, oldest first.

    Args:
        available: (dump_id, directory name) pairs on the FTP server.
        imported_ids: dump ids already loaded since the latest full dump.
        after_dump_id: id of the latest full dump; dumps at or below it are already
            covered by that full dump. ``None`` keeps every available dump.
    """
    missing = [
        dump for dump in available
        if dump[0] not in imported_ids and (after_dump_id is None or dump[0] > after_dump_id)
    ]
    missing.sort(key=lambda dump: dump[0])
    return missing
