import signal
import time

from flask import current_app
from sqlalchemy import text

from listenbrainz.background.delete import delete_listens_history, delete_user
from listenbrainz.background.export import export_user
from listenbrainz.webserver import create_app, db_conn, ts_conn
from listenbrainz.background.listens_importer import import_listens

CLAIM_TIMEOUT_HOURS = 6
MAX_TASK_RETRIES = 3


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
    Tasks that have exceeded MAX_TASK_RETRIES are excluded so they do not starve the queue.
    """
    result = db_conn.execute(text(f"""
        WITH claimable AS (
            SELECT id
              FROM background_tasks
             WHERE (claimed_at IS NULL
                OR claimed_at < now() - interval '{CLAIM_TIMEOUT_HOURS} hours')
               AND retries < :max_retries
          ORDER BY created
             LIMIT 1
               FOR UPDATE SKIP LOCKED
        )
        UPDATE background_tasks
           SET claimed_at = now()
         WHERE id = (SELECT id FROM claimable)
     RETURNING *
    """), {"max_retries": MAX_TASK_RETRIES})
    task = result.first()
    db_conn.commit()
    return task


def release_task(task, error=None):
    """ Release a claimed task so it can be retried by another worker.

    Increments the retry counter and records the error message if provided.
    If MAX_TASK_RETRIES is reached, the task will not be re-claimed.
    """
    params = {"id": task.id, "last_error": str(error) if error else None}
    db_conn.execute(text("""
        UPDATE background_tasks
           SET claimed_at = NULL,
               retries = retries + 1,
               last_error = COALESCE(:last_error, last_error)
         WHERE id = :id
    """), params)
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
        if task.task == "delete_listens":
            delete_listens_history(db_conn, task.user_id, task.created)
        elif task.task == "delete_user":
            delete_user(db_conn, ts_conn, task.user_id, task.created)
        elif task.task == "export_all_user_data":
            export_user(db_conn, ts_conn, task.user_id, task.metadata)
        elif task.task == "import_listens":
            import_listens(db_conn, ts_conn, task.user_id, task.metadata)
        else:
            current_app.logger.error(f"Unknown task type: {task}")

    def _release_on_shutdown(self, signum, frame):
        """ Best-effort release of the current task on SIGTERM (docker stop, deploys). """
        if self._current_task:
            try:
                # Do not increment retries or mark error on graceful container shutdown
                db_conn.execute(text("""
                    UPDATE background_tasks SET claimed_at = NULL WHERE id = :id
                """), {"id": self._current_task.id})
                db_conn.commit()
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
                except Exception as err:
                    current_app.logger.error("Error processing task:", exc_info=True)
                    release_task(task, error=err)
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
                ts_conn.rollback()


if __name__ == "__main__":
    bt = BackgroundTasks()
    with create_app().app_context():
        bt.start()
