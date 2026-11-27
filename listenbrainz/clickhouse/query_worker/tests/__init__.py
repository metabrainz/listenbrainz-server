"""Database tests use the ClickHouse service started by ./test.sh.

Each test owns a fresh database, including worker connections opened by the dump
loader. A missing server is a test failure, never a silent skip. For a server
outside Compose, set CLICKHOUSE_TEST_HOST/PORT/USERNAME/PASSWORD.
"""

import os
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

import clickhouse_connect
import pyarrow.parquet as pq
import requests
from sqlalchemy import create_engine

from listenbrainz import config
from listenbrainz.clickhouse.query_worker.client import ClickHouseConnection
from listenbrainz.clickhouse.query_worker.listens.ftp import DumpType
from listenbrainz.clickhouse.query_worker.listens.load_dump import (
    STAGING_TABLE_PREFIX, _load_parquet_files, _prepare_import, read_archive,
)
from listenbrainz.clickhouse.query_worker.listens.schema import LISTEN_COLUMN_NAMES, ensure_schema
from listenbrainz.clickhouse.query_worker.query_map import functions
from listenbrainz.clickhouse.result_consumer.handlers import get_handler
from listenbrainz.db import couchdb, listens

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


def archive_parquet_files(directory: Path, destination: Path) -> Path:
    with tarfile.open(destination, "w") as archive:
        for path in sorted(directory.rglob("*.parquet")):
            archive.add(path, arcname=str(path.relative_to(directory)))
    return destination


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

    def assert_hourly_counts_match_listens(self):
        expected = self.client.query("""
            SELECT user_id, toDate(listened_at, 'UTC') AS day, toHour(listened_at, 'UTC') AS hour,
                   count()
              FROM listens GROUP BY user_id, day, hour ORDER BY user_id, day, hour
        """).result_rows
        actual = self.client.query("""
            SELECT user_id, day, hour, sum(listen_count) AS total
              FROM hourly_listen_counts GROUP BY user_id, day, hour HAVING total != 0
             ORDER BY user_id, day, hour
        """).result_rows
        self.assertEqual(actual, expected)

    def staging_tables(self) -> list[str]:
        return [name for (name,) in self.client.query(
            "SELECT name FROM system.tables WHERE database = currentDatabase() AND startsWith(name, {prefix:String})",
            parameters={"prefix": STAGING_TABLE_PREFIX},
        ).result_rows]


class DumpImportTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        config = listens.create_test_listens_connect_strings()
        self.listens_engine = create_engine(config["DB_CONNECT"])
        self.addCleanup(self.listens_engine.dispose)
        with self.listens_engine.connect() as conn:
            self.assertEqual(conn.exec_driver_sql("SELECT current_database()").scalar_one(), config["DB_NAME"])
        self.clear_deletion_records()
        self.addCleanup(self.clear_deletion_records)

    def clear_deletion_records(self):
        with self.listens_engine.begin() as conn:
            conn.exec_driver_sql("TRUNCATE listen_delete_metadata, deleted_user_listen_history")

    def load_archive(self, archive: Path, dump_type: DumpType):
        """Exercise the shared loader with a local test archive."""
        parquet_files, _ = read_archive(archive)
        _prepare_import(self.connection, self.listens_engine)
        result = _load_parquet_files(parquet_files, self.connection, dump_type, workers=2)
        self.assert_hourly_counts_match_listens()
        return result

    def load_fixture(self, name):
        dump_type = DumpType.FULL if name.startswith("full") else DumpType.INCREMENTAL
        with TemporaryDirectory() as tmp:
            archive = archive_parquet_files(TEST_DATA_PATH / name, Path(tmp) / "dump.tar")
            result = self.load_archive(archive, dump_type)
        self.assertEqual(result["errors"], [])
        self.assertGreater(result["total_inserted"], 0)
        return result

    def load_spark_listens(self):
        for name in ("full-dump-1", "incremental-dump-2", "incremental-dump-3"):
            self.load_fixture(name)


class ActivityTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        couchdb.init(config.COUCHDB_USER, config.COUCHDB_ADMIN_KEY, config.COUCHDB_HOST,
                     config.COUCHDB_PORT, config.COUCHDB_DATABASE_PREFIX)
        prefix = patch.object(couchdb, "_database_prefix", f"test_{uuid4().hex}_")
        prefix.start()
        self.addCleanup(prefix.stop)
        self.addCleanup(self.clean_databases)

    def clean_databases(self):
        for database in couchdb.list_databases(""):
            requests.delete(couchdb._get_database_url(database)).raise_for_status()

    def refresh(self, ranges):
        with patch.object(type(self.connection), "from_config", return_value=self.connection):
            messages = list(functions[self.query_name](ranges))
        for message in messages:
            get_handler(message["type"])(message)
        return messages
