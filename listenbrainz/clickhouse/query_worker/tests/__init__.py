"""Database tests use the ClickHouse service started by ./test.sh.

Each test owns a fresh database, including worker connections opened by the dump
loader. A missing server is a test failure, never a silent skip. For a server
outside Compose, set CLICKHOUSE_TEST_HOST/PORT/USERNAME/PASSWORD.
"""

import os
import unittest
from pathlib import Path
from uuid import uuid4

import clickhouse_connect
import pyarrow.parquet as pq

from listenbrainz.clickhouse.query_worker.client import ClickHouseConnection
from listenbrainz.clickhouse.query_worker.listens.ftp import DumpType
from listenbrainz.clickhouse.query_worker.listens.load_dump import STAGING_TABLE_PREFIX, load_dump
from listenbrainz.clickhouse.query_worker.listens.schema import LISTEN_COLUMN_NAMES, ensure_schema

TEST_DATA_PATH = Path(__file__).resolve().parents[4] / "listenbrainz_spark" / "testdata"


def _normalized(row: dict) -> tuple:
    """A listen as a comparable tuple, whether read from Parquet or from ClickHouse."""
    def value(name):
        v = row[name]
        if name in ("listened_at", "created"):
            return int(v.timestamp() * 1000)
        if name == "artist_credit_mbids":
            return tuple(str(mbid) for mbid in v or [])
        if name in ("recording_msid", "release_mbid", "recording_mbid"):
            return None if v is None else str(v)
        return v
    return tuple(value(name) for name in LISTEN_COLUMN_NAMES)


def fixture_listens(*names) -> set[tuple]:
    """All columns of the listens of the fixture dumps ``names``."""
    return {_normalized(row) for name in names for path in (TEST_DATA_PATH / name).glob("*.parquet")
            for row in pq.read_table(path).to_pylist()}


class ClickHouseTestCase(unittest.TestCase):
    def setUp(self):
        server = {
            "host": os.environ.get("CLICKHOUSE_TEST_HOST", "clickhouse"),
            "port": int(os.environ.get("CLICKHOUSE_TEST_PORT", "8123")),
            "username": os.environ.get("CLICKHOUSE_TEST_USERNAME", "listenbrainz"),
            "password": os.environ.get("CLICKHOUSE_TEST_PASSWORD", "listenbrainz"),
        }
        admin = clickhouse_connect.get_client(**server)
        self.addCleanup(admin.close)
        database = "test_listens_" + uuid4().hex
        admin.command(f"CREATE DATABASE {database}")
        self.addCleanup(admin.command, f"DROP DATABASE {database} SYNC")
        self.connection = ClickHouseConnection(**server, database=database)
        self.client = self.connection.connect()
        self.addCleanup(self.client.close)
        ensure_schema(self.client)

    def listens(self) -> list[tuple]:
        """All columns of the listens in ClickHouse, sorted."""
        result = self.client.query(f"SELECT {', '.join(LISTEN_COLUMN_NAMES)} FROM listens")
        return sorted(_normalized(dict(zip(result.column_names, row))) for row in result.result_rows)

    def staging_tables(self) -> list[str]:
        return [name for (name,) in self.client.query(
            "SELECT name FROM system.tables WHERE database = currentDatabase() AND startsWith(name, {prefix:String})",
            parameters={"prefix": STAGING_TABLE_PREFIX},
        ).result_rows]

    def load_fixture(self, name):
        dump_type = DumpType.FULL if name.startswith("full") else DumpType.INCREMENTAL
        result = load_dump(str(TEST_DATA_PATH / name), self.connection, dump_type, workers=2)
        self.assertEqual(result["errors"], [])
        self.assertGreater(result["total_inserted"], 0)
        return result

    def load_spark_listens(self):
        for name in ("full-dump-1", "incremental-dump-2", "incremental-dump-3"):
            self.load_fixture(name)
