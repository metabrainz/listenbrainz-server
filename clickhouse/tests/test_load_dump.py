import shutil
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq

from clickhouse.stats.activity_cache_manager import ActivityStatsCacheManager
from clickhouse.stats.ftp import DumpType
from clickhouse.stats.load_dump import (
    build_raw_listens_arrow_table,
    drop_raw_listens_partition,
    load_dump,
    process_raw_listens,
)
from clickhouse.tests import ClickHouseTestCase, TEST_DATA_PATH


class DumpDataTestCase(ClickHouseTestCase):
    def rows(self):
        return self.client.query("SELECT user_id, listened_at, recording_msid FROM listens ORDER BY user_id, listened_at, recording_msid").result_rows

    def test_fixture_import_and_replay_are_idempotent(self):
        self.load_spark_listens()
        rows = self.rows()
        expected = {(r["user_id"], int(r["listened_at"].timestamp()), r["recording_msid"])
                    for name in ("full-dump-1", "incremental-dump-2", "incremental-dump-3")
                    for path in (TEST_DATA_PATH / name).glob("*.parquet") for r in pq.read_table(path).to_pylist()}
        self.assertEqual({(uid, int(ts.timestamp()), msid) for uid, ts, msid in rows}, expected)
        self.assertEqual(len(rows), len(expected))
        # replaying incremental dumps adds nothing
        self.load_fixture("incremental-dump-2")
        self.load_fixture("incremental-dump-3")
        self.assertEqual(self.rows(), rows)
        # a full dump followed by its incrementals gives the same listens again
        self.load_spark_listens()
        self.assertEqual(self.rows(), rows)
        self.assertEqual(self.client.query("SELECT count() FROM raw_listens").first_row[0], 0)

    def test_processing_skips_loaded_listens_and_isolates_load_partitions(self):
        source = pq.read_table(TEST_DATA_PATH / "incremental-dump-2" / "0.parquet")
        self.client.insert_arrow("raw_listens", build_raw_listens_arrow_table(source, "one"))
        other = source.slice(0, 1).set_column(source.schema.get_field_index("user_id"), "user_id", pa.array([999], type=pa.int64()))
        self.client.insert_arrow("raw_listens", build_raw_listens_arrow_table(other, "two"))
        process_raw_listens(self.client, "one")
        self.assertEqual(len(self.rows()), source.num_rows)
        self.assertNotIn(999, {r[0] for r in self.rows()})
        # processing the same load again adds nothing
        process_raw_listens(self.client, "one")
        self.assertEqual(len(self.rows()), source.num_rows)
        drop_raw_listens_partition(self.client, "one")
        self.assertEqual(self.client.query("SELECT DISTINCT load_id FROM raw_listens").result_rows, [("two",)])
        process_raw_listens(self.client, "two")
        self.assertIn(999, {r[0] for r in self.rows()})

    def test_full_dump_clears_stats_and_drops_deleted_listens(self):
        self.load_spark_listens()
        manager = self.manager(ActivityStatsCacheManager, "daily_activity")
        list(manager.run_hourly_job())
        self.assertGreater(self.client.query("SELECT count() FROM user_stats_cache_state").first_row[0], 0)
        fixture = [r for path in sorted((TEST_DATA_PATH / "full-dump-1").glob("*.parquet"))
                   for r in pq.read_table(path).to_pylist()]
        row = tuple(fixture[0][key] for key in ("user_id", "listened_at", "recording_msid", "created"))
        self.client.insert("deleted_listens", [(1, *row)], column_names=["id", "user_id", "listened_at", "recording_msid", "created"])
        deleted_user = next(r["user_id"] for r in fixture if r["user_id"] != row[0])
        cutoff = max(r["created"] for r in fixture if r["user_id"] == deleted_user)
        self.client.insert("deleted_user_listen_history", [(1, deleted_user, cutoff)],
                           column_names=["id", "user_id", "max_created"])
        self.load_fixture("full-dump-1")
        for table in ("user_stats_cache_state", "stats_cache_state"):
            self.assertEqual(self.client.query(f"SELECT count() FROM {table}").first_row[0], 0)
        self.assertEqual(self.client.query("SELECT count() FROM deleted_listens").first_row[0], 1)
        self.assertNotIn(tuple(row[:3]), self.rows())
        self.assertNotIn(deleted_user, {uid for uid, _, _ in self.rows()})

    def test_failed_replace_keeps_existing_listens_and_stats(self):
        self.load_spark_listens()
        list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        before = self.rows()
        state = self.client.query("SELECT count() FROM user_stats_cache_state").first_row[0]
        with TemporaryDirectory() as tmp:
            shutil.copy(TEST_DATA_PATH / "incremental-dump-2" / "0.parquet", Path(tmp) / "good.parquet")
            (Path(tmp) / "bad.parquet").write_bytes(b"not parquet")
            failed = load_dump(tmp, self.connection, DumpType.FULL, workers=2)
        self.assertEqual(len(failed["errors"]), 1)
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.client.query("SELECT count() FROM user_stats_cache_state").first_row[0], state)
        self.assertEqual(self.client.query(
            "SELECT count() FROM system.tables WHERE database = currentDatabase() AND name = 'listens_replace'"
        ).first_row[0], 0)

    def test_full_dump_swaps_in_only_the_dump(self):
        self.load_spark_listens()
        self.load_fixture("full-dump-1")
        expected = {(r["user_id"], int(r["listened_at"].timestamp()), r["recording_msid"])
                    for path in (TEST_DATA_PATH / "full-dump-1").glob("*.parquet") for r in pq.read_table(path).to_pylist()}
        self.assertEqual({(uid, int(ts.timestamp()), msid) for uid, ts, msid in self.rows()}, expected)
        self.assertEqual(self.client.query(
            "SELECT count() FROM system.tables WHERE database = currentDatabase() AND name = 'listens_replace'"
        ).first_row[0], 0)

    def test_backfilled_listens_force_recompute(self):
        self.load_spark_listens()
        manager = self.manager(ActivityStatsCacheManager, "daily_activity")
        list(manager.run_hourly_job())
        old = datetime(2021, 7, 15)
        table = pa.table({"user_id": [1], "listened_at": [old], "created": [old], "recording_msid": ["backfilled"]})
        with TemporaryDirectory() as tmp:
            pq.write_table(table, Path(tmp) / "listens.parquet")
            self.assertEqual(load_dump(tmp, self.connection)["errors"], [])
        messages = list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        self.assertEqual({u["user_id"] for m in messages for u in m.get("data", [])}, {1})

    def test_deleted_history_filters_old_rows_but_keeps_resubmissions(self):
        ts = datetime(2021, 7, 1)
        self.client.insert("deleted_user_listen_history", [(1, 1, ts)], column_names=["id", "user_id", "max_created"])
        table = pa.table({"user_id": [1, 1, 2], "listened_at": [ts] * 3,
                          "created": [ts, ts + timedelta(seconds=1), ts], "recording_msid": ["old", "new", "other"]})
        with TemporaryDirectory() as tmp:
            pq.write_table(table, Path(tmp) / "listens.parquet")
            result = load_dump(tmp, self.connection)
        self.assertEqual(result["errors"], [])
        self.assertEqual({(uid, msid) for uid, _, msid in self.rows()}, {(1, "new"), (2, "other")})
