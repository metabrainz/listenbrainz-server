"""High-water marks of the incremental imports into ClickHouse, kept in ``import_state``.

Dump imports keep the id of the last incremental dump in listens: a full dump import
restarts it at the full dump, and the catch-up loads incremental dumps oldest first and
stops at the first failure, so every dump up to the mark is loaded.
"""

from clickhouse_connect.driver import Client

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
        """
        INSERT INTO import_state (name, last_id, version)
        SELECT {name:String}, {last_id:UInt64}, (SELECT max(version) + 1 FROM import_state)
        """,
        parameters={"name": name, "last_id": last_id},
        settings={"async_insert": 0},
    )
