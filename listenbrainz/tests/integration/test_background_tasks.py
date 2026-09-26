import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.background.background_tasks import (
    MAX_TASK_RETRIES,
    BackgroundTasks,
    add_task,
    claim_task,
    peek_task,
    release_task,
    remove_task,
)
from listenbrainz.tests.integration import NonAPIIntegrationTestCase
from listenbrainz.webserver import db_conn


class BackgroundTasksTestCase(NonAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1999, "test-bg-tasks-user")
        db_user.agree_to_gdpr(self.db_conn, self.user["musicbrainz_id"])
        # Clean up any existing background tasks before each test
        self.db_conn.execute(text("DELETE FROM background_tasks"))
        self.db_conn.commit()

    def tearDown(self):
        self.db_conn.execute(text("DELETE FROM background_tasks"))
        self.db_conn.commit()
        super().tearDown()

    def test_add_and_peek_task(self):
        add_task(self.user["id"], "delete_listens")
        task = peek_task()
        self.assertIsNotNone(task)
        self.assertEqual(task.user_id, self.user["id"])
        self.assertEqual(task.task, "delete_listens")
        self.assertEqual(task.retries, 0)
        self.assertIsNone(task.last_error)

    def test_claim_and_remove_task(self):
        add_task(self.user["id"], "delete_listens")
        task = claim_task()
        self.assertIsNotNone(task)
        self.assertIsNotNone(task.claimed_at)

        # Once claimed, claiming again should yield nothing
        self.assertIsNone(claim_task())

        remove_task(task)
        self.assertIsNone(peek_task())

    def test_release_task_increments_retries_and_sets_error(self):
        add_task(self.user["id"], "delete_listens")
        task = claim_task()
        self.assertEqual(task.retries, 0)

        # Release task with an error message
        test_err = RuntimeError("Temporary network timeout")
        release_task(task, error=test_err)

        reclaimed = claim_task()
        self.assertIsNotNone(reclaimed)
        self.assertEqual(reclaimed.retries, 1)
        self.assertEqual(reclaimed.last_error, "Temporary network timeout")

    def test_task_exceeding_max_retries_is_not_reclaimed(self):
        """ Verify that a failing task that reaches MAX_TASK_RETRIES is excluded

        from claim_task(), preventing queue starvation for other users.
        """
        # Add a poison-pill task for user 1
        add_task(self.user["id"], "delete_listens")

        # Simulate failures up to MAX_TASK_RETRIES
        for attempt in range(MAX_TASK_RETRIES):
            task = claim_task()
            self.assertIsNotNone(task, f"Task should be claimable on attempt {attempt + 1}")
            release_task(task, error=f"Fatal error on attempt {attempt + 1}")

        # After MAX_TASK_RETRIES, the poison task must NOT be claimed again
        self.assertIsNone(claim_task())

        # Now add a second, valid task for another user or the same user
        add_task(self.user["id"], "delete_user")
        next_task = claim_task()
        self.assertIsNotNone(next_task)
        self.assertEqual(next_task.task, "delete_user")
        self.assertEqual(next_task.retries, 0)
