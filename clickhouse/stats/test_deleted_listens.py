import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2.extensions import make_dsn

from clickhouse.stats import deleted_listens as dl
from clickhouse.stats.activity_cache_manager import ActivityStatsCacheManager
from clickhouse.tests import ClickHouseTestCase


class DeletedListensTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        dsn = os.environ.get("CLICKHOUSE_TEST_TIMESCALE_DSN", "postgresql://postgres:postgres@lb_db/postgres")
        pg = psycopg2.connect(dsn)
        self.addCleanup(pg.close)
        pg.autocommit = True
        cursor = pg.cursor()
        self.addCleanup(cursor.close)
        schema = "test_clickhouse_" + uuid4().hex
        cursor.execute(f"CREATE SCHEMA {schema}")
        self.addCleanup(cursor.execute, f"DROP SCHEMA {schema} CASCADE")
        cursor.execute(f"SET search_path TO {schema}")
        self.dsn = make_dsn(dsn, options=f"-c search_path={schema}")
        # Use the production table/type definitions, isolated from other test data.
        root = Path(__file__).resolve().parents[2] / "admin" / "timescale"
        types = (root / "create_types.sql").read_text()
        cursor.execute(re.search(r"CREATE TYPE listen_delete_metadata_status_enum[^;]+;", types).group())
        tables = (root / "create_tables.sql").read_text()
        for name in ("listen_delete_metadata", "deleted_user_listen_history"):
            cursor.execute(re.search(rf"CREATE TABLE {name} \([^;]+;", tables).group())
        self.pg = cursor

    def test_import_deletions_and_retry_against_real_databases(self):
        self.load_spark_listens()
        original = self.client.query("SELECT user_id, listened_at, created, recording_msid FROM listens ORDER BY user_id, listened_at").result_rows
        manager = self.manager(ActivityStatsCacheManager, "daily_activity")
        list(manager.run_hourly_job())
        deleted = [r for r in original if r[0] == 1][:2]
        pending = [r for r in original if r[0] == 1][2]
        for row, status in [(r, "complete") for r in deleted] + [(pending, "pending")]:
            uid, listened_at, created, msid = row
            self.pg.execute("INSERT INTO listen_delete_metadata (user_id, listened_at, recording_msid, status, listen_created) VALUES (%s, %s, %s, %s, %s)",
                            (uid, listened_at, msid, status, created))
        # A re-submission has the same listen identity but a newer creation time.
        uid, listened_at, created, msid = deleted[0]
        resubmitted = (uid, listened_at, created + timedelta(days=365), msid)
        self.insert_listens([resubmitted])
        summary = dl.import_deleted_listens(self.dsn, self.client, batch_size=1)
        self.assertEqual(summary["deleted_listens_imported"], 2)
        self.assertEqual(summary["deleted_listens_removed"], 2)
        expected = [r for r in original if r not in deleted] + [resubmitted]
        self.assertCountEqual(self.client.query("SELECT user_id, listened_at, created, recording_msid FROM listens").result_rows, expected)
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_LISTENS_STATE), 2)
        # Explicitly wait for mutations before inspecting their results.
        self.client.command("ALTER TABLE user_stats_cache_state DELETE WHERE 0 SETTINGS mutations_sync=2")
        self.assertEqual({r[0] for r in self.client.query("SELECT DISTINCT user_id FROM user_stats_cache_state").result_rows}, {2})
        retry = dl.import_deleted_listens(self.dsn, self.client, batch_size=1)
        self.assertEqual(retry["deleted_listens_imported"], 0)
        self.assertEqual(retry["deleted_listens_removed"], 0)
        self.load_spark_listens()
        self.assertCountEqual(self.client.query("SELECT user_id, listened_at, created, recording_msid FROM listens").result_rows, expected)
        # Completing the pending deletion makes it eligible on the next import.
        self.pg.execute("UPDATE listen_delete_metadata SET status = 'complete' WHERE status = 'pending'")
        self.assertEqual(dl.import_deleted_listens(self.dsn, self.client)["deleted_listens_removed"], 1)
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_LISTENS_STATE), 3)

    def test_history_deletion_keeps_newer_listens_and_other_users(self):
        old = datetime(2021, 7, 1, tzinfo=timezone.utc)
        new = old + timedelta(seconds=1)
        self.insert_listens([(1, old, old, "old"), (1, old, new, "new"), (2, old, old, "other")])
        self.pg.execute("INSERT INTO deleted_user_listen_history (user_id, max_created) VALUES (%s, %s)", (1, old))
        result = dl.import_deleted_listens(self.dsn, self.client, batch_size=1)
        self.assertEqual(result["deleted_user_histories_imported"], 1)
        self.assertEqual(result["deleted_user_listens_removed"], 1)
        self.assertEqual(self.client.query("SELECT recording_msid FROM listens ORDER BY recording_msid").result_rows, [("new",), ("other",)])
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_USER_HISTORY_STATE), 1)
        self.assertEqual(dl.import_deleted_listens(self.dsn, self.client)["deleted_user_histories_imported"], 0)

    def test_import_state_is_persistent_and_isolated_by_source(self):
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_LISTENS_STATE), 0)
        dl.set_import_state(self.client, dl.DELETED_LISTENS_STATE, 10)
        dl.set_import_state(self.client, dl.DELETED_LISTENS_STATE, 20)
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_LISTENS_STATE), 20)
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_USER_HISTORY_STATE), 0)
