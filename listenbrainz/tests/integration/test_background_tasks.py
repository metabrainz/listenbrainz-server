from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.background.background_tasks import add_task, claim_task, defer_task
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import db_conn


class BackgroundTasksTestCase(IntegrationTestCase):

    def test_failed_task_is_deferred(self):
        user_1 = db_user.get_or_create(self.db_conn, 1, "user_1")
        user_2 = db_user.get_or_create(self.db_conn, 2, "user_2")

        with self.app.app_context():
            add_task(user_1["id"], "delete_user")
            add_task(user_2["id"], "delete_user")

            failed = claim_task()
            self.assertEqual(failed.user_id, user_1["id"])
            defer_task(failed)

            # the failed task must not block the queue or be retried immediately
            self.assertEqual(claim_task().user_id, user_2["id"])
            self.assertIsNone(claim_task())

            # once the retry delay has passed it becomes claimable again
            db_conn.execute(
                text("UPDATE background_tasks SET claimed_at = claimed_at - interval '11 minutes' WHERE id = :id"),
                {"id": failed.id},
            )
            db_conn.commit()
            self.assertEqual(claim_task().id, failed.id)
