"""High-water marks of the incremental imports into ClickHouse, kept in ``import_state``.

Listen deletions keep the last copied row id of each source table. Dump imports keep
the id of the last incremental dump in listens: the catch-up loads dumps oldest first
and stops at the first failure, so every dump up to the mark is loaded.
"""

from clickhouse_connect.driver import Client

from clickhouse.stats.ftp import DumpType

INCREMENTAL_DUMP_STATE = "incremental_dump"


def get_import_state(ch_client: Client, name: str) -> int:
    """The last id imported for ``name``, 0 if there is none."""
    result = ch_client.query(
        "SELECT last_id FROM import_state FINAL WHERE name = {name:String}",
        parameters={"name": name},
    )
    return result.first_row[0] if result.result_rows else 0


def set_import_state(ch_client: Client, name: str, last_id: int) -> None:
    ch_client.command(
        "INSERT INTO import_state (name, last_id) VALUES ({name:String}, {last_id:UInt64})",
        parameters={"name": name, "last_id": last_id},
    )


def record_imported_dump(ch_client: Client, dump_id: int, dump_type: DumpType) -> None:
    """Advance the incremental dump mark after dump ``dump_id`` loaded cleanly.

    A full dump restarts it at the full dump: listens now hold that dump and nothing
    newer. An incremental dump only moves it forward.
    """
    if dump_type == DumpType.FULL:
        last_id = dump_id
    else:
        last_id = max(dump_id, get_import_state(ch_client, INCREMENTAL_DUMP_STATE))
    set_import_state(ch_client, INCREMENTAL_DUMP_STATE, last_id)
