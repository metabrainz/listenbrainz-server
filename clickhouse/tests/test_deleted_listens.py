import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
import sqlalchemy

from clickhouse.stats import deleted_listens as dl
from clickhouse.stats.activity_cache_manager import ActivityStatsCacheManager
from clickhouse.stats.cache_manager import FORCE_RECOMPUTE_CREATED
from clickhouse.stats.ftp import DumpType
from clickhouse.stats.load_dump import load_dump
from clickhouse.tests import ClickHouseTestCase
from listenbrainz.db import listens as listens_db
from listenbrainz.db.testing import TimescaleTestCase
from listenbrainz.listenstore.timescale_listenstore import TimescaleListenStore

T0 = datetime(2021, 7, 1, tzinfo=timezone.utc)


class DeletedListensTestCase(ClickHouseTestCase):
    """Deletions made through ListenBrainz in its listens test database, applied to ClickHouse."""

    def setUp(self):
        super().setUp()
        connect = listens_db.create_test_listens_connect_strings()
        listens_db.init_db_connection(connect["DB_CONNECT"])
        TimescaleTestCase.reset_listens_db(self)
        self.dsn = connect["DB_CONNECT"]
        self.listenstore = TimescaleListenStore(logging.getLogger(__name__))

    def submit(self, created: datetime, *listens: tuple[int, datetime, str]) -> None:
        """Submit (user_id, listened_at, recording_msid) listens to the listens database."""
        listens_db.insert([(listened_at, created, user_id, msid, "{}") for user_id, listened_at, msid in listens])

    def dump(self, created_after: datetime | None = None) -> str:
        """Write the listens database as a Spark dump would: all listens, or those created after a time."""
        query = "SELECT listened_at, created, user_id, recording_msid::text AS recording_msid FROM listen"
        params = {}
        if created_after is not None:
            query += " WHERE created > :created_after"
            params["created_after"] = created_after
        with listens_db.engine.connect() as connection:
            rows = [dict(row._mapping) for row in connection.execute(sqlalchemy.text(query), params)]
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        pq.write_table(pa.Table.from_pylist(rows), Path(directory.name) / "0.parquet")
        return directory.name

    def load(self, directory: str, dump_type: DumpType) -> None:
        self.assertEqual(load_dump(directory, self.connection, dump_type)["errors"], [])

    def import_deletions(self) -> dict:
        return dl.import_deleted_listens(self.dsn, self.client, batch_size=1)

    def clickhouse_listens(self) -> set[tuple]:
        rows = self.client.query("SELECT user_id, listened_at, recording_msid FROM listens").result_rows
        return {(user_id, listened_at.replace(tzinfo=timezone.utc), msid) for user_id, listened_at, msid in rows}

    def forced_users(self) -> set[int]:
        rows = self.client.query(
            "SELECT DISTINCT user_id FROM user_stats_cache_state FINAL"
            " WHERE last_computed_created = toDateTime64({forced:String}, 3)",
            parameters={"forced": FORCE_RECOMPUTE_CREATED},
        ).result_rows
        return {row[0] for row in rows}

    def test_listen_deletion(self):
        a, b, c, d = (str(uuid4()) for _ in range(4))
        self.submit(T0, (1, T0, a), (1, T0 + timedelta(hours=1), b), (1, T0 + timedelta(hours=2), c),
                    (2, T0, d))
        full_dump = self.dump()
        self.load(full_dump, DumpType.FULL)
        manager = self.manager(ActivityStatsCacheManager, "daily_activity")
        list(manager.run_hourly_job())

        # Deleting a listen only queues it; ClickHouse imports it once the cron job processed it.
        self.listenstore.delete_listen(T0, 1, a)
        self.listenstore.delete_listen(T0 + timedelta(hours=1), 1, b)
        self.listenstore.delete_listen(T0, 1, str(uuid4()))  # no such listen: marked invalid
        self.assertEqual(self.import_deletions()["deleted_listens_imported"], 0)

        listens_db.delete_pending_listens()
        summary = self.import_deletions()
        self.assertEqual(summary["deleted_listens_imported"], 2)
        self.assertEqual(summary["deleted_listens_removed"], 2)
        remaining = {(1, T0 + timedelta(hours=2), c), (2, T0, d)}
        self.assertEqual(self.clickhouse_listens(), remaining)
        self.assertEqual(self.forced_users(), {1})
        recomputed = list(manager.run_hourly_job())
        self.assertEqual({u["user_id"] for m in recomputed for u in m.get("data", [])}, {1})
        self.assertEqual(self.import_deletions()["deleted_listens_imported"], 0)

        # The full dump predates the deletion, reloading it keeps the deleted listens out.
        self.load(full_dump, DumpType.FULL)
        self.assertEqual(self.clickhouse_listens(), remaining)

        # A re-submission is a new listen (newer created) and comes back with the next dump.
        resubmitted = T0 + timedelta(days=1)
        self.submit(resubmitted, (1, T0, a))
        self.load(self.dump(created_after=T0), DumpType.INCREMENTAL)
        self.assertEqual(self.clickhouse_listens(), remaining | {(1, T0, a)})

    def test_history_deletion(self):
        old, other, new = str(uuid4()), str(uuid4()), str(uuid4())
        self.submit(T0, (1, T0, old), (2, T0, other))
        full_dump = self.dump()
        self.load(full_dump, DumpType.FULL)

        cutoff = T0 + timedelta(hours=1)
        self.listenstore.delete(1, created=cutoff)
        # listens submitted after the deletion are kept
        self.submit(cutoff + timedelta(hours=1), (1, T0 + timedelta(days=1), new))
        self.load(self.dump(created_after=T0), DumpType.INCREMENTAL)

        summary = self.import_deletions()
        self.assertEqual(summary["deleted_user_histories_imported"], 1)
        self.assertEqual(summary["deleted_user_listens_removed"], 1)
        kept = {(1, T0 + timedelta(days=1), new), (2, T0, other)}
        self.assertEqual(self.clickhouse_listens(), kept)
        self.assertEqual(self.import_deletions()["deleted_user_histories_imported"], 0)

        # Reloading the dumps made before the deletion keeps the deleted history out.
        self.load(full_dump, DumpType.FULL)
        self.load(self.dump(created_after=T0), DumpType.INCREMENTAL)
        self.assertEqual(self.clickhouse_listens(), kept)

    def test_import_state_is_persistent_and_isolated_by_source(self):
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_LISTENS_STATE), 0)
        dl.set_import_state(self.client, dl.DELETED_LISTENS_STATE, 10)
        dl.set_import_state(self.client, dl.DELETED_LISTENS_STATE, 20)
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_LISTENS_STATE), 20)
        self.assertEqual(dl.get_import_state(self.client, dl.DELETED_USER_HISTORY_STATE), 0)
