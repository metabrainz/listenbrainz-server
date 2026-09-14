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

from clickhouse.stats.cache_manager import CacheConfig
from clickhouse.stats.load_dump import load_dump
from clickhouse.stats.schema import ensure_stats_schema

TEST_DATA_PATH = Path(__file__).resolve().parents[2] / "listenbrainz_spark" / "testdata"


class ClickHouseTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = {
            "host": os.environ.get("CLICKHOUSE_TEST_HOST", "clickhouse"),
            "port": int(os.environ.get("CLICKHOUSE_TEST_PORT", "8123")),
            "username": os.environ.get("CLICKHOUSE_TEST_USERNAME", "listenbrainz"),
            "password": os.environ.get("CLICKHOUSE_TEST_PASSWORD", "listenbrainz"),
        }
        admin = clickhouse_connect.get_client(**self.connection)
        self.addCleanup(admin.close)
        database = "test_stats_" + uuid4().hex
        admin.command(f"CREATE DATABASE {database}")
        self.addCleanup(admin.command, f"DROP DATABASE {database} SYNC")
        self.connection["database"] = database
        self.client = clickhouse_connect.get_client(**self.connection)
        self.addCleanup(self.client.close)
        ensure_stats_schema(self.client)
        self.cache_config = CacheConfig(**{f"ch_{key}": value for key, value in self.connection.items()})

    def manager(self, manager_class, stat_type):
        manager = manager_class(self.cache_config, stat_type)
        manager.connect()
        self.addCleanup(manager.ch_client.close)
        return manager

    def load_fixture(self, name, **kwargs):
        result = load_dump(str(TEST_DATA_PATH / name), **self.connection, workers=2, **kwargs)
        self.assertEqual(result["errors"], [])
        self.assertGreater(result["total_inserted"], 0)
        return result

    def load_spark_listens(self):
        for name in ("full-dump-1", "incremental-dump-2", "incremental-dump-3"):
            self.load_fixture(name)

    def insert_listens(self, rows):
        self.client.insert("listens", rows, column_names=["user_id", "listened_at", "created", "recording_msid"])
