import shutil
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq

from clickhouse.stats.activity_cache_manager import ActivityStatsCacheManager
from clickhouse.stats.load_dump import build_raw_listens_arrow_table, load_dump, process_raw_listens, drop_raw_listens_partition
from clickhouse.stats.schema import ensure_stats_schema
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
        for chunks in (1, 4):
            with self.subTest(chunks=chunks):
                self.load_fixture("full-dump-1", process_chunks=chunks)
                self.load_fixture("incremental-dump-2", process_chunks=chunks)
                self.assertEqual(self.rows(), rows)
                self.assertEqual(self.client.query("SELECT count() FROM raw_listens").first_row[0], 0)

    def test_processing_deduplicates_and_isolates_load_partitions(self):
        source = pq.read_table(TEST_DATA_PATH / "incremental-dump-2" / "0.parquet")
        self.client.insert_arrow("raw_listens", build_raw_listens_arrow_table(pa.concat_tables([source, source]), "one"))
        other = source.slice(0, 1).set_column(source.schema.get_field_index("user_id"), "user_id", pa.array([999], type=pa.int64()))
        self.client.insert_arrow("raw_listens", build_raw_listens_arrow_table(other, "two"))
        process_raw_listens(self.client, "one", chunks=4)
        self.assertEqual(len(self.rows()), len({(r["user_id"], r["listened_at"], r["recording_msid"]) for r in source.to_pylist()}))
        self.assertNotIn(999, {r[0] for r in self.rows()})
        drop_raw_listens_partition(self.client, "one")
        self.assertEqual(self.client.query("SELECT DISTINCT load_id FROM raw_listens").result_rows, [("two",)])
        process_raw_listens(self.client, "two")
        self.assertIn(999, {r[0] for r in self.rows()})

    def test_replace_clears_stats_but_preserves_deletions(self):
        self.load_spark_listens()
        manager = self.manager(ActivityStatsCacheManager, "daily_activity")
        list(manager.run_hourly_job())
        self.assertGreater(self.client.query("SELECT count() FROM user_stats_cache_state").first_row[0], 0)
        fixture = pq.read_table(TEST_DATA_PATH / "full-dump-1" / "0.parquet").to_pylist()[0]
        row = tuple(fixture[key] for key in ("user_id", "listened_at", "recording_msid", "created"))
        self.client.insert("deleted_listens", [(1, *row)], column_names=["id", "user_id", "listened_at", "recording_msid", "created"])
        self.load_fixture("full-dump-1", replace=True)
        for table in ("user_stats_cache_state", "stats_cache_state"):
            self.assertEqual(self.client.query(f"SELECT count() FROM {table}").first_row[0], 0)
        self.assertEqual(self.client.query("SELECT count() FROM deleted_listens").first_row[0], 1)
        self.assertNotIn(tuple(row[:3]), self.rows())

    def test_failed_replace_keeps_existing_listens_and_stats(self):
        self.load_spark_listens()
        list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        before = self.rows()
        state = self.client.query("SELECT count() FROM user_stats_cache_state").first_row[0]
        with TemporaryDirectory() as tmp:
            shutil.copy(TEST_DATA_PATH / "incremental-dump-2" / "0.parquet", Path(tmp) / "good.parquet")
            (Path(tmp) / "bad.parquet").write_bytes(b"not parquet")
            failed = load_dump(tmp, self.connection, workers=2, replace=True)
        self.assertEqual(len(failed["errors"]), 1)
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.client.query("SELECT count() FROM user_stats_cache_state").first_row[0], state)
        self.assertEqual(self.client.query(
            "SELECT count() FROM system.tables WHERE database = currentDatabase() AND name = 'listens_replace'"
        ).first_row[0], 0)

    def test_replace_swaps_in_only_the_dump(self):
        self.load_spark_listens()
        self.load_fixture("full-dump-1", replace=True)
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

    def test_corrupt_file_does_not_publish_partial_dump(self):
        self.load_fixture("full-dump-1")
        before = self.rows()
        with TemporaryDirectory() as tmp:
            shutil.copy(TEST_DATA_PATH / "incremental-dump-2" / "0.parquet", Path(tmp) / "good.parquet")
            (Path(tmp) / "bad.parquet").write_bytes(b"not parquet")
            failed = load_dump(tmp, self.connection, workers=2)
            self.assertEqual(len(failed["errors"]), 1)
            self.assertEqual(failed["files_completed"], 1)
            self.assertEqual(self.rows(), before)
            self.assertGreater(self.client.query("SELECT count() FROM raw_listens").first_row[0], 0)
            (Path(tmp) / "bad.parquet").unlink()
            retried = load_dump(tmp, self.connection)
            self.assertEqual(retried["errors"], [])
        self.assertGreater(len(self.rows()), len(before))
        self.assertEqual(self.client.query("SELECT DISTINCT load_id FROM raw_listens").result_rows, [(failed["load_id"],)])

    def test_schema_initialization_preserves_existing_data(self):
        self.load_fixture("full-dump-1")
        before = self.rows()
        ensure_stats_schema(self.client)
        self.assertEqual(self.rows(), before)

    def test_legacy_staging_schema_migrates_only_when_empty(self):
        self.client.command("DROP TABLE raw_listens")
        self.client.command("CREATE TABLE raw_listens (user_id UInt32) ENGINE = MergeTree ORDER BY user_id")
        self.client.insert("raw_listens", [(1,)], column_names=["user_id"])
        with self.assertRaisesRegex(RuntimeError, "still holds 1 rows"):
            ensure_stats_schema(self.client)
        self.assertEqual(self.client.query("SELECT * FROM raw_listens").result_rows, [(1,)])
        self.client.command("TRUNCATE TABLE raw_listens")
        ensure_stats_schema(self.client)
        self.assertEqual(self.client.query("SELECT partition_key FROM system.tables WHERE database = currentDatabase() AND name = 'raw_listens'").first_row[0], "load_id")
