import json
from datetime import datetime, timezone
from unittest import mock

from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

import listenbrainz.db.user as db_user
from listenbrainz import db
from listenbrainz.background.background_tasks import BackgroundTasks, MAX_CONSECUTIVE_ERRORS, add_task, claim_task, defer_task, release_task, remove_task
from listenbrainz.background.registry import TASKS
from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.db import background, user_data_export
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import db_conn


# The test environment runs a background_tasks worker against the same database, which would claim and run the
# tasks these tests set up before the tests claim them. These tests use their own copies of the task tables instead,
# in a schema the worker does not look at. "user" and every other table still resolve to public.
ISOLATED_SCHEMA = "background_tasks_test"
ISOLATED_TABLES = ["background_tasks", "user_data_import"]


def _use_isolated_schema(dbapi_connection, connection_record):
    with dbapi_connection.cursor() as cursor:
        cursor.execute(f"SET search_path TO {ISOLATED_SCHEMA}, public")


class BackgroundTasksTestCase(IntegrationTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with db.engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {ISOLATED_SCHEMA} CASCADE"))
            connection.execute(text(f"CREATE SCHEMA {ISOLATED_SCHEMA}"))
            for table in ISOLATED_TABLES:
                connection.execute(text(
                    f"CREATE TABLE {ISOLATED_SCHEMA}.{table} (LIKE public.{table} INCLUDING ALL)"
                ))

    @classmethod
    def tearDownClass(cls):
        with db.engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {ISOLATED_SCHEMA} CASCADE"))
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # the base classes set up a new engine, the listener goes on the one the test uses
        self._engine = db.engine
        event.listen(self._engine, "connect", _use_isolated_schema)

    def tearDown(self):
        # the base tear down clears the tables, which must still be the isolated copies
        super().tearDown()
        event.remove(self._engine, "connect", _use_isolated_schema)

    def test_tables_are_isolated_from_the_worker(self):
        with self.app.app_context():
            schema = db_conn.execute(text(
                "SELECT schemaname FROM pg_tables WHERE tablename = 'background_tasks' AND schemaname = current_schema()"
            )).scalar()
        self.assertEqual(schema, ISOLATED_SCHEMA)

    def _insert_task(self, user_id, task, metadata=None, **columns):
        names = ", ".join(["user_id", "task", "metadata", *columns])
        values = ", ".join([":user_id", ":task", ":metadata", *[f":{c}" for c in columns]])
        db_conn.execute(
            text(f"INSERT INTO background_tasks ({names}) VALUES ({values})"),
            {"user_id": user_id, "task": task, "metadata": json.dumps(metadata or {}), **columns},
        )
        db_conn.commit()

    def _update(self, sql, **params):
        db_conn.execute(text(sql), params)
        db_conn.commit()

    def _row(self, task_id):
        return db_conn.execute(text("SELECT * FROM background_tasks WHERE id = :id"), {"id": task_id}).first()

    def _tasks(self, user_id):
        rows = db_conn.execute(
            text("SELECT task FROM background_tasks WHERE user_id = :user_id ORDER BY id"), {"user_id": user_id}
        )
        return [row.task for row in rows]

    def test_failed_task_is_deferred(self):
        user_1 = db_user.get_or_create(self.db_conn, 1, "user_1")
        user_2 = db_user.get_or_create(self.db_conn, 2, "user_2")

        with self.app.app_context():
            add_task(user_1["id"], "delete_user")
            add_task(user_2["id"], "delete_user")

            failed = claim_task(TASKS["delete_user"])
            self.assertEqual(failed.user_id, user_1["id"])
            defer_task(failed, TASKS["delete_user"], "boom")

            # the failed task must not block the queue or be retried immediately
            self.assertEqual(claim_task(TASKS["delete_user"]).user_id, user_2["id"])
            self.assertIsNone(claim_task(TASKS["delete_user"]))

            # once the retry delay has passed it becomes claimable again
            self._update("UPDATE background_tasks SET due_at = due_at - interval '11 minutes' WHERE id = :id", id=failed.id)
            self.assertEqual(claim_task(TASKS["delete_user"]).id, failed.id)

    def test_user_tasks_run_one_at_a_time_in_order(self):
        user_1 = db_user.get_or_create(self.db_conn, 1, "user_1")
        user_2 = db_user.get_or_create(self.db_conn, 2, "user_2")

        with self.app.app_context():
            self._insert_task(user_1["id"], "export_all_user_data", {"export_id": 1})
            add_task(user_1["id"], "delete_listens")
            add_task(user_2["id"], "delete_listens")

            # user_1's delete waits for their earlier export, other users' deletes do not
            self.assertEqual(claim_task(TASKS["delete_listens"]).user_id, user_2["id"])
            self.assertIsNone(claim_task(TASKS["delete_listens"]))

            export = claim_task(TASKS["export_all_user_data"])
            self.assertEqual(export.task, "export_all_user_data")
            self.assertIsNone(claim_task(TASKS["delete_listens"]))

            remove_task(export)
            delete = claim_task(TASKS["delete_listens"])
            self.assertEqual((delete.user_id, delete.task), (user_1["id"], "delete_listens"))

    def test_deferred_task_still_blocks_later_tasks(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context():
            self._insert_task(user["id"], "export_all_user_data", {"export_id": 1})
            add_task(user["id"], "delete_listens")

            export = claim_task(TASKS["export_all_user_data"])
            defer_task(export, TASKS["export_all_user_data"], "boom")

            # the delete must not run while the export waits to be retried
            self.assertIsNone(claim_task(TASKS["delete_listens"]))

    def test_expired_claim_does_not_block_the_lane(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context():
            self._insert_task(user["id"], "export_all_user_data", {"export_id": 1})
            add_task(user["id"], "delete_listens")
            # a worker was killed while running the later task
            self._update("""
                UPDATE background_tasks SET claimed_at = now() - interval '7 hours', attempts = 1
                 WHERE user_id = :user_id AND task = 'delete_listens'
            """, user_id=user["id"])

            self.assertEqual(claim_task(TASKS["export_all_user_data"]).task, "export_all_user_data")

    def test_task_fails_after_max_attempts(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        task_type = TASKS["export_all_user_data"]

        with self.app.app_context():
            self._insert_task(user["id"], "export_all_user_data", {"export_id": 1})
            with self.assertLogs(self.app.logger, "ERROR") as logs:
                for _ in range(task_type.max_attempts):
                    task = claim_task(task_type)
                    defer_task(task, task_type, "boom")
                    self._update("UPDATE background_tasks SET due_at = now() - interval '1 minute' WHERE id = :id", id=task.id)

            row = self._row(task.id)
            self.assertIsNotNone(row.failed_at)
            self.assertEqual(row.last_error, "boom")
            self.assertIsNone(claim_task(task_type))
            self.assertTrue(any(f"Task {task.id} failed" in line for line in logs.output))

    def test_retry_delay_is_capped_at_an_hour(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        task_type = TASKS["delete_user"]

        with self.app.app_context():
            add_task(user["id"], "delete_user")
            task = claim_task(task_type)
            self._update("UPDATE background_tasks SET attempts = 20")
            defer_task(self._row(task.id), task_type, "listens database is down")

            delay = db_conn.execute(text("SELECT due_at - now() FROM background_tasks")).scalar()
            self.assertLessEqual(delay.total_seconds(), 3600)

    def test_failed_task_does_not_block_later_tasks(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context():
            self._insert_task(user["id"], "export_all_user_data", {"export_id": 1}, failed_at="2026-11-01T00:00:00Z")
            add_task(user["id"], "delete_listens")

            self.assertEqual(claim_task(TASKS["delete_listens"]).task, "delete_listens")

    def test_failed_delete_can_be_requested_again(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context():
            self._insert_task(user["id"], "delete_user", failed_at="2026-11-01T00:00:00Z")
            add_task(user["id"], "delete_user")

            self.assertEqual(self._tasks(user["id"]), ["delete_user", "delete_user"])

    def test_expired_claim_uses_task_timeout(self):
        user_1 = db_user.get_or_create(self.db_conn, 1, "user_1")
        user_2 = db_user.get_or_create(self.db_conn, 2, "user_2")

        with self.app.app_context():
            add_task(user_1["id"], "delete_user")
            self._insert_task(user_2["id"], "import_listens", {"import_id": 1})
            self._update("UPDATE background_tasks SET claimed_at = now() - interval '31 minutes', attempts = 1")

            self.assertEqual(claim_task(TASKS["delete_user"]).user_id, user_1["id"])
            self.assertIsNone(claim_task(TASKS["import_listens"]))

    def test_expired_claim_counts_as_attempt(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context():
            add_task(user["id"], "delete_user")
            self._update(
                "UPDATE background_tasks SET claimed_at = now() - interval '31 minutes', attempts = :attempts",
                attempts=TASKS["delete_user"].max_attempts,
            )

            with self.assertLogs(self.app.logger, "ERROR") as logs:
                self.assertIsNone(claim_task(TASKS["delete_user"]))
            self.assertTrue(any("failed" in line for line in logs.output))
            row = db_conn.execute(text("SELECT * FROM background_tasks")).first()
            self.assertIsNotNone(row.failed_at)
            self.assertEqual(row.last_error, "worker stopped before finishing")

    def test_release_does_not_count_attempt(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context():
            add_task(user["id"], "delete_user")
            task = claim_task(TASKS["delete_user"])
            release_task(task)

            self.assertEqual(self._row(task.id).attempts, 0)

    def test_add_task_rejects_unknown_type(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context(), self.assertRaises(ValueError):
            add_task(user["id"], "nope")

    def _create_import(self, user_id):
        background.create_import_task(
            db_conn,
            user_id=user_id,
            service="spotify",
            from_date=datetime(2021, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
            file_path="spotify.zip",
            filename="spotify.zip",
        )
        db_conn.commit()

    def _import_count(self, user_id):
        return db_conn.execute(
            text("SELECT count(*) FROM user_data_import WHERE user_id = :user_id"), {"user_id": user_id}
        ).scalar()

    @mock.patch("listenbrainz.background.background_tasks.delete_import_file")
    def test_delete_cancels_waiting_imports_not_exports(self, mock_delete_file):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context():
            self._create_import(user["id"])
            self._insert_task(user["id"], "export_all_user_data", {"export_id": 1})

            add_task(user["id"], "delete_listens")

            self.assertEqual(self._tasks(user["id"]), ["export_all_user_data", "delete_listens"])
            self.assertEqual(self._import_count(user["id"]), 0)
            mock_delete_file.assert_called_once_with("spotify.zip")

    @mock.patch("listenbrainz.background.background_tasks.delete_import_file")
    def test_delete_waits_for_running_import_to_stop(self, mock_delete_file):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")

        with self.app.app_context():
            self._create_import(user["id"])
            running = claim_task(TASKS["import_listens"])
            self._update("""UPDATE user_data_import SET metadata = metadata || '{"status": "in_progress"}'""")

            add_task(user["id"], "delete_listens")

            # the running import keeps its task row, and so the user's slot, until it stops
            self.assertEqual(self._tasks(user["id"]), ["import_listens", "delete_listens"])
            self.assertIsNone(claim_task(TASKS["delete_listens"]))
            mock_delete_file.assert_not_called()

            remove_task(running)
            self.assertEqual(claim_task(TASKS["delete_listens"]).task, "delete_listens")

    @mock.patch("listenbrainz.background.listens_importer.base.delete_import_file")
    @mock.patch("listenbrainz.background.listens_importer.base.download_import_file", return_value="spotify.zip")
    def test_running_import_stops_once_cancelled(self, mock_download, mock_delete_file):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        batches = []

        class CancelledDuringImport(BaseListensImporter):
            def process_import_file(self, import_task):
                batches.append(1)
                # the user asks to delete their listens while the first batch is being read
                self.db_conn.execute(text("DELETE FROM user_data_import"))
                self.db_conn.commit()
                yield [{}]
                batches.append(2)
                yield [{}]

            def parse_listen_batch(self, batch):
                return []

        with self.app.app_context():
            self._create_import(user["id"])
            import_task = db_conn.execute(text("SELECT * FROM user_data_import")).mappings().first()
            importer = CancelledDuringImport(db_conn, None)
            with mock.patch.object(importer, "submit_listens") as mock_submit:
                importer.import_listens(user["id"], dict(import_task))

            mock_submit.assert_not_called()
            self.assertEqual(batches, [1])
            mock_delete_file.assert_called_once_with("spotify.zip")

    @mock.patch("listenbrainz.background.background_tasks.ERROR_RETRY_SECONDS", 0)
    def test_worker_survives_a_claim_error(self):
        worker = BackgroundTasks()
        calls = []

        def claim(task_type):
            calls.append(task_type.name)
            if len(calls) == 1:
                raise OperationalError("SELECT 1", {}, Exception("server closed the connection"))
            worker._stop.set()
            return None

        with mock.patch("listenbrainz.background.background_tasks.claim_task", side_effect=claim):
            worker.work(self.app, TASKS["delete_user"])

        # the first error did not stop the worker, it claimed again
        self.assertEqual(calls, ["delete_user", "delete_user"])

    def test_stale_worker_cannot_touch_a_reclaimed_task(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        task_type = TASKS["delete_user"]

        with self.app.app_context():
            add_task(user["id"], "delete_user")
            stale = claim_task(task_type)
            # the first worker ran past the timeout and another thread claimed the task again
            self._update("UPDATE background_tasks SET claimed_at = now() - interval '31 minutes' WHERE id = :id", id=stale.id)
            live = claim_task(task_type)
            self.assertEqual(live.id, stale.id)

            remove_task(stale)
            release_task(stale)
            defer_task(stale, task_type, "boom")

            row = self._row(live.id)
            self.assertEqual(row.claimed_at, live.claimed_at)
            self.assertEqual(row.attempts, live.attempts)
            self.assertIsNone(row.last_error)

    def test_export_that_fails_for_good_is_marked_failed(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        task_type = TASKS["export_all_user_data"]

        with self.app.app_context():
            export = user_data_export.request_user_data_export(db_conn, user["id"])
            db_conn.execute(text("UPDATE user_data_export SET status = 'in_progress'"))
            # the worker was killed on every attempt
            self._update(
                "UPDATE background_tasks SET claimed_at = now() - interval '7 hours', attempts = :attempts",
                attempts=task_type.max_attempts,
            )

            self.assertIsNone(claim_task(task_type))
            status = db_conn.execute(
                text("SELECT status FROM user_data_export WHERE id = :id"), {"id": export["export_id"]}
            ).scalar()
            self.assertEqual(status, "failed")

    @mock.patch("listenbrainz.background.listens_importer.delete_import_file")
    def test_import_that_fails_for_good_is_marked_failed(self, mock_delete_file):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        task_type = TASKS["import_listens"]

        with self.app.app_context():
            self._create_import(user["id"])
            task = claim_task(task_type)
            self._update("UPDATE background_tasks SET attempts = :attempts", attempts=task_type.max_attempts)
            task = self._row(task.id)

            defer_task(task, task_type, "boom")

            status = db_conn.execute(text("SELECT metadata->>'status' FROM user_data_import")).scalar()
            self.assertEqual(status, "failed")
            mock_delete_file.assert_called_once_with("spotify.zip")

    @mock.patch("listenbrainz.background.background_tasks.ERROR_RETRY_SECONDS", 0)
    def test_idle_thread_does_not_add_up_separate_errors(self):
        worker = BackgroundTasks()
        error = OperationalError("SELECT 1", {}, Exception("server closed the connection"))
        # five database blips, each followed by a successful poll that found nothing to do
        results = [error, None] * MAX_CONSECUTIVE_ERRORS
        calls = []

        def claim(task_type):
            calls.append(task_type.name)
            if not results:
                worker._stop.set()
                return None
            result = results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with mock.patch("listenbrainz.background.background_tasks.claim_task", side_effect=claim), \
                mock.patch.object(self.app.config, "get", return_value=0):
            worker.work(self.app, TASKS["delete_user"])

        self.assertEqual(len(calls), 2 * MAX_CONSECUTIVE_ERRORS + 1)
