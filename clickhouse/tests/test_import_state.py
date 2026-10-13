from datetime import datetime, timedelta

from clickhouse.stats.ftp import DumpType
from clickhouse.stats.import_state import INCREMENTAL_DUMP_STATE, get_import_state, record_imported_dump
from clickhouse.stats.schema import ensure_stats_schema
from clickhouse.tests import ClickHouseTestCase


class ImportStateTestCase(ClickHouseTestCase):

    def mark(self):
        return get_import_state(self.client, INCREMENTAL_DUMP_STATE)

    def test_incremental_dumps_advance_the_mark(self):
        self.assertEqual(self.mark(), 0)
        record_imported_dump(self.client, 2501, DumpType.INCREMENTAL)
        self.assertEqual(self.mark(), 2501)
        # a manual load of an older dump does not move it back
        record_imported_dump(self.client, 2490, DumpType.INCREMENTAL)
        self.assertEqual(self.mark(), 2501)

    def test_full_dump_restarts_the_mark(self):
        record_imported_dump(self.client, 2501, DumpType.INCREMENTAL)
        record_imported_dump(self.client, 2490, DumpType.FULL)
        self.assertEqual(self.mark(), 2490)


class SeedIncrementalDumpStateTestCase(ClickHouseTestCase):

    def create_imported_dumps(self, rows):
        self.client.command("""
            CREATE TABLE imported_dumps (
                dump_id UInt64,
                dump_type LowCardinality(String),
                imported_at DateTime64(3)
            ) ENGINE = ReplacingMergeTree(imported_at)
            ORDER BY (dump_type, dump_id)
        """)
        self.client.insert("imported_dumps", rows, column_names=["dump_id", "dump_type", "imported_at"])

    def mark(self):
        return get_import_state(self.client, INCREMENTAL_DUMP_STATE)

    def test_seeds_from_latest_full_dump_and_incrementals_imported_after_it(self):
        base = datetime(2026, 6, 10, 0, 21, 48, 531000)
        self.create_imported_dumps([
            (2400, "full", base - timedelta(days=30)),
            (2450, "incremental", base - timedelta(days=1)),  # superseded by the newer full dump
            (2500, "full", base),
            (2501, "incremental", base + timedelta(milliseconds=1)),
            (2502, "incremental", base + timedelta(days=1)),
        ])
        ensure_stats_schema(self.client)
        self.assertEqual(self.mark(), 2502)

    def test_seeds_full_dump_without_later_incrementals(self):
        base = datetime(2026, 6, 10)
        self.create_imported_dumps([(2490, "incremental", base), (2500, "full", base + timedelta(seconds=1))])
        ensure_stats_schema(self.client)
        self.assertEqual(self.mark(), 2500)

    def test_seeds_incrementals_without_full_dump(self):
        self.create_imported_dumps([(10, "incremental", datetime(2026, 6, 10))])
        ensure_stats_schema(self.client)
        self.assertEqual(self.mark(), 10)

    def test_existing_mark_and_empty_table_are_left_alone(self):
        self.create_imported_dumps([])
        ensure_stats_schema(self.client)
        self.assertEqual(self.mark(), 0)
        record_imported_dump(self.client, 7, DumpType.FULL)
        self.client.insert("imported_dumps", [(2500, "full", datetime(2026, 6, 10))],
                           column_names=["dump_id", "dump_type", "imported_at"])
        ensure_stats_schema(self.client)
        self.assertEqual(self.mark(), 7)
