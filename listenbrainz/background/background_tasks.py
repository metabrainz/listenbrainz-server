import signal
import time

from flask import current_app
from sqlalchemy import text

from listenbrainz.background import delete, export, listens_importer
from listenbrainz.background.registry import TASKS
from listenbrainz.webserver import create_app, db_conn, listens_conn

CLAIM_TIMEOUT_HOURS = 6
FAILED_TASK_RETRY_MINUTES = 10


def add_task(user_id, task):
    """ Add a task to the background tasks """
    query = "INSERT INTO background_tasks (user_id, task) VALUES (:user_id, :task) ON CONFLICT DO NOTHING"
    db_conn.execute(text(query), {"user_id": user_id, "task": task})
    db_conn.commit()


def peek_task():
    """ Return the oldest background task without claiming it.

    Used by tests to verify a task was queued. Workers must use claim_task().
    """
    result = db_conn.execute(text("SELECT * FROM background_tasks ORDER BY created LIMIT 1"))
    return result.first()


def claim_task():
    """ Claim the oldest unclaimed task using FOR UPDATE SKIP LOCKED.

    The lock is only held for the duration of the UPDATE — once committed,
    the claim survives any intermediate commits during processing.
    Crashed workers' tasks are auto-reclaimed after CLAIM_TIMEOUT_HOURS.
    """
    result = db_conn.execute(text(f"""
        WITH claimable AS (
            SELECT id
              FROM background_tasks
             WHERE claimed_at IS NULL
                OR claimed_at < now() - interval '{CLAIM_TIMEOUT_HOURS} hours'
          ORDER BY created
             LIMIT 1
               FOR UPDATE SKIP LOCKED
        )
        UPDATE background_tasks
           SET claimed_at = now()
         WHERE id = (SELECT id FROM claimable)
     RETURNING *
    """))
    task = result.first()
    db_conn.commit()
    return task


def release_task(task):
    """ Release a claimed task so it can be retried by another worker. """
    db_conn.execute(text("""
        UPDATE background_tasks SET claimed_at = NULL WHERE id = :id
    """), {"id": task.id})
    db_conn.commit()


def defer_task(task):
    """ Keep a failed task claimed so it is retried after FAILED_TASK_RETRY_MINUTES.

    Releasing it instead would make it the oldest claimable task again, so the worker would
    retry it immediately in a tight loop and every task queued after it would starve.
    """
    # backdate the claim so that claim_task considers it expired after the retry delay
    db_conn.execute(text(f"""
        UPDATE background_tasks
           SET claimed_at = now() - interval '{CLAIM_TIMEOUT_HOURS} hours' + interval '{FAILED_TASK_RETRY_MINUTES} minutes'
         WHERE id = :id
    """), {"id": task.id})
    db_conn.commit()


def remove_task(task):
    """ Delete a completed task. """
    db_conn.execute(text("DELETE FROM background_tasks WHERE id = :id"), {"id": task.id})
    db_conn.commit()


class BackgroundTasks:

    def __init__(self):
        self._current_task = None

    def process_task(self, task):
        """ Perform the task """
        current_app.logger.info(f"Processing task: {task.id}")
        task_type = TASKS.get(task.task)
        if task_type is None:
            current_app.logger.error(f"Unknown task type: {task}")
            return
        task_type.handler(db_conn, listens_conn, task)

    def _release_on_shutdown(self, signum, frame):
        """ Best-effort release of the current task on SIGTERM (docker stop, deploys). """
        if self._current_task:
            try:
                release_task(self._current_task)
                current_app.logger.info("Released task %s on shutdown.", self._current_task.id)
            except Exception:
                current_app.logger.error("Failed to release task %s on shutdown:", self._current_task.id, exc_info=True)
        raise SystemExit(0)

    def start(self):
        current_app.logger.info("Background tasks processor started.")
        signal.signal(signal.SIGTERM, self._release_on_shutdown)
        while True:
            try:
                task = claim_task()
                if task is None:
                    time.sleep(current_app.config.get("BACKGROUND_TASKS_SLEEP_TIME", 5))
                    continue
                self._current_task = task
                try:
                    self.process_task(task)
                    remove_task(task)
                except Exception:
                    current_app.logger.error("Error processing task:", exc_info=True)
                    db_conn.rollback()
                    defer_task(task)
                finally:
                    self._current_task = None
            except KeyboardInterrupt:
                current_app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                current_app.logger.error("Error in background tasks processor:", exc_info=True)
                time.sleep(2)
                current_app.logger.info("Exiting process, letting container restart.")
                break
            finally:
                # I suspect the following line is related to this failure:
                # https://gist.github.com/mayhem/fbd21a146fd34f291cced7dee7e7fca7
                # But, sadly it doesn't stop the failure -- there is some other connection
                # that has a transaction open, making everything cranky. Until we find
                # the root cause of this problem (tricky!) we can mitigate this better
                # by simply exiting the container when this happens and start fresh.
                db_conn.rollback()
                listens_conn.rollback()


if __name__ == "__main__":
    bt = BackgroundTasks()
    with create_app().app_context():
        bt.start()
