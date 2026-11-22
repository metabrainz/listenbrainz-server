import signal
import time

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from listenbrainz.background import delete, export, listens_importer
from listenbrainz.background.registry import TASKS
from listenbrainz.webserver import create_app, db_conn, listens_conn

FAILED_TASK_RETRY_MINUTES = 10
MAX_RETRY_DELAY_MINUTES = 60


def add_task(user_id, task):
    """ Add a task to the background tasks

    Raises:
        ValueError: if no task type with this name is registered
    """
    if task not in TASKS:
        raise ValueError(f"Unknown background task: {task}")
    query = "INSERT INTO background_tasks (user_id, task) VALUES (:user_id, :task) ON CONFLICT DO NOTHING"
    db_conn.execute(text(query), {"user_id": user_id, "task": task})
    db_conn.commit()


def peek_task():
    """ Return the oldest background task without claiming it.

    Used by tests to verify a task was queued. Workers must use claim_task().
    """
    result = db_conn.execute(text("SELECT * FROM background_tasks ORDER BY created LIMIT 1"))
    return result.first()


def claim_task(task_type):
    """ Claim the oldest due task of this type using FOR UPDATE SKIP LOCKED.

    A user's tasks run one at a time, in creation order: a task is skipped while the same user
    has a claimed task or any earlier task that has not failed, even one waiting to be retried.
    The lock is only held for the duration of the UPDATE, once committed the claim survives any
    intermediate commits during processing.

    Args:
        task_type: the registered TaskType to claim a task of

    Returns:
        the claimed background_tasks row, or None if no task of this type can run now
    """
    # a claim older than its type's timeout means the worker died. Expired claims of every type are
    # released, since the unique index on claimed tasks would otherwise block that user's other tasks.
    types = list(TASKS.values())
    released = db_conn.execute(text("""
        UPDATE background_tasks bt
           SET claimed_at = NULL
             , failed_at = CASE WHEN bt.attempts >= t.max_attempts THEN now() END
             , last_error = CASE WHEN bt.attempts >= t.max_attempts THEN 'worker stopped before finishing' ELSE bt.last_error END
          FROM (SELECT unnest(CAST(:names AS background_tasks_type[])) AS task
                     , unnest(CAST(:timeouts AS interval[])) AS timeout
                     , unnest(CAST(:max_attempts AS integer[])) AS max_attempts) t
         WHERE bt.task = t.task
           AND bt.claimed_at < now() - t.timeout
     RETURNING bt.*
    """), {
        "names": [t.name for t in types],
        "timeouts": [t.timeout for t in types],
        "max_attempts": [t.max_attempts for t in types],
    }).all()
    db_conn.commit()
    for row in released:
        if row.failed_at is not None:
            _task_failed(TASKS[row.task], row, row.last_error)
    try:
        result = db_conn.execute(text("""
            WITH claimable AS (
                SELECT bt.id
                  FROM background_tasks bt
                 WHERE bt.task = :task
                   AND bt.due_at <= now()
                   AND bt.claimed_at IS NULL
                   AND bt.failed_at IS NULL
                   AND NOT EXISTS (
                        SELECT 1
                          FROM background_tasks other
                         WHERE other.user_id = bt.user_id
                           AND (other.claimed_at IS NOT NULL
                                OR ((other.created, other.id) < (bt.created, bt.id) AND other.failed_at IS NULL))
                   )
              ORDER BY bt.created, bt.id
                 LIMIT 1
                   FOR UPDATE OF bt SKIP LOCKED
            )
            UPDATE background_tasks
               SET claimed_at = now()
                 , attempts = attempts + 1
             WHERE id = (SELECT id FROM claimable)
         RETURNING *
        """), {"task": task_type.name})
        task = result.first()
        db_conn.commit()
    except IntegrityError:
        # another thread claimed a task of the same user at the same moment
        db_conn.rollback()
        return None
    return task


def _task_failed(task_type, task, error):
    """ Log a task that will not be retried again and let its type record the failure where the user sees it. """
    current_app.logger.error("Task %s failed after %d attempts, it will not be retried: %s", task.id, task.attempts, error)
    if task_type.on_failed is None:
        return
    try:
        task_type.on_failed(db_conn, task)
    except Exception:
        current_app.logger.error("Could not record the failure of task %s:", task.id, exc_info=True)
        db_conn.rollback()


# release_task, defer_task and remove_task only act on the claim the caller holds: a worker that ran past
# the timeout may find the task claimed again by another thread, and must leave that claim alone

def release_task(task):
    """ Release a claimed task so it can be retried by another worker, without using up an attempt. """
    db_conn.execute(text("""
        UPDATE background_tasks SET claimed_at = NULL, attempts = attempts - 1 WHERE id = :id AND claimed_at = :claimed_at
    """), {"id": task.id, "claimed_at": task.claimed_at})
    db_conn.commit()


def defer_task(task, task_type, error):
    """ Release a failed task to be retried later, or mark it failed after its last attempt.

    Args:
        task: the claimed background_tasks row
        task_type: the registered TaskType of the task
        error: a description of the failure, kept in last_error
    """
    failed = task.attempts >= task_type.max_attempts
    if failed:
        query = """
            UPDATE background_tasks
               SET claimed_at = NULL, failed_at = now(), last_error = :error
             WHERE id = :id AND claimed_at = :claimed_at
        """
    else:
        # backing off keeps a failing task from being retried in a tight loop ahead of the queue
        query = f"""
            UPDATE background_tasks
               SET claimed_at = NULL
                 , due_at = now() + LEAST(interval '{FAILED_TASK_RETRY_MINUTES} minutes' * attempts,
                                          interval '{MAX_RETRY_DELAY_MINUTES} minutes')
                 , last_error = :error
             WHERE id = :id AND claimed_at = :claimed_at
        """
    result = db_conn.execute(text(query), {"id": task.id, "error": error, "claimed_at": task.claimed_at})
    db_conn.commit()
    if failed and result.rowcount == 1:
        _task_failed(task_type, task, error)


def remove_task(task):
    """ Delete a completed task. """
    db_conn.execute(
        text("DELETE FROM background_tasks WHERE id = :id AND claimed_at = :claimed_at"),
        {"id": task.id, "claimed_at": task.claimed_at},
    )
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
                task = next(filter(None, (claim_task(task_type) for task_type in TASKS.values())), None)
                if task is None:
                    time.sleep(current_app.config.get("BACKGROUND_TASKS_SLEEP_TIME", 5))
                    continue
                self._current_task = task
                try:
                    self.process_task(task)
                    remove_task(task)
                except Exception as e:
                    current_app.logger.error("Error processing task:", exc_info=True)
                    db_conn.rollback()
                    defer_task(task, TASKS[task.task], str(e))
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
