import signal
import sys
import threading

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from listenbrainz.background import delete, export, listens_importer
from listenbrainz.background.listens_importer.storage import delete_import_file
from listenbrainz.background.registry import TASKS
from listenbrainz.webserver import create_app, db_conn, listens_conn

FAILED_TASK_RETRY_MINUTES = 10
MAX_RETRY_DELAY_MINUTES = 60
ERROR_RETRY_SECONDS = 5
MAX_CONSECUTIVE_ERRORS = 5
DELETE_TASKS = ("delete_user", "delete_listens")


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
    # after the insert, so a failed insert never leaves the imports cancelled with nothing deleted
    if task in DELETE_TASKS:
        cancel_imports(user_id)


def cancel_imports(user_id):
    """ Cancel the user's unfinished imports so that a delete does not wait behind them.

    Exports are left alone, so "export my data, then delete my listens" still leaves the user with
    their export. A running import notices that its row is gone at its next batch and stops. Its
    task row stays until then, so the delete cannot start while the import is still submitting listens.

    Args:
        user_id: the ListenBrainz row ID of the user
    """
    imports = db_conn.execute(text("""
        DELETE FROM user_data_import
              WHERE user_id = :user_id
                AND metadata->>'status' IN ('waiting', 'in_progress')
          RETURNING file_path, metadata->>'status' AS status
    """), {"user_id": user_id}).all()
    db_conn.execute(text("""
        DELETE FROM background_tasks
              WHERE user_id = :user_id
                AND task = 'import_listens'
                AND claimed_at IS NULL
    """), {"user_id": user_id})
    db_conn.commit()
    for row in imports:
        # a running import deletes its own file when it stops
        if row.status == "waiting":
            delete_import_file(row.file_path)


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
        self._current_tasks = {}
        self._stop = threading.Event()

    def process_task(self, task):
        """ Perform the task """
        current_app.logger.info(f"Processing task: {task.id}")
        task_type = TASKS.get(task.task)
        if task_type is None:
            current_app.logger.error(f"Unknown task type: {task}")
            return
        task_type.handler(db_conn, listens_conn, task)

    def _release_current_tasks(self):
        for task in list(self._current_tasks.values()):
            try:
                release_task(task)
                current_app.logger.info("Released task %s on shutdown.", task.id)
            except Exception:
                current_app.logger.error("Failed to release task %s on shutdown:", task.id, exc_info=True)

    def _release_on_shutdown(self, signum, frame):
        """ Release the tasks the threads are running on SIGTERM (docker stop, deploys). """
        self._stop.set()
        self._release_current_tasks()
        raise SystemExit(0)

    def _run(self, task_type, progress):
        """ Claim and run tasks of one type until stopped.

        Args:
            task_type: the registered TaskType to run
            progress: a dict whose "claimed" is set to True once a claim has reached the database
        """
        thread = threading.current_thread()
        while not self._stop.is_set():
            task = claim_task(task_type)
            # a claim that reached the database, whether or not it found a task, ends a run of errors
            progress["claimed"] = True
            if task is not None and self._stop.is_set():
                # claimed after shutdown released the claims, give it back before the process exits
                release_task(task)
                return
            if task is None:
                self._stop.wait(current_app.config.get("BACKGROUND_TASKS_SLEEP_TIME", 5))
                continue
            self._current_tasks[thread] = task
            try:
                self.process_task(task)
                remove_task(task)
            except Exception as e:
                current_app.logger.error("Error processing task:", exc_info=True)
                db_conn.rollback()
                defer_task(task, task_type, str(e))
            finally:
                self._current_tasks.pop(thread, None)
                # I suspect the following line is related to this failure:
                # https://gist.github.com/mayhem/fbd21a146fd34f291cced7dee7e7fca7
                # But, sadly it doesn't stop the failure -- there is some other connection
                # that has a transaction open, making everything cranky.
                db_conn.rollback()
                listens_conn.rollback()

    def work(self, app, task_type):
        """ Run tasks of one type on this thread until the worker stops.

        An error outside a task, e.g. the database restarting, is retried with new connections.
        After MAX_CONSECUTIVE_ERRORS in a row the whole process stops so the container restarts.
        """
        errors = 0
        while not self._stop.is_set():
            with app.app_context():
                progress = {"claimed": False}
                try:
                    self._run(task_type, progress)
                except Exception:
                    current_app.logger.error("Error in background tasks processor:", exc_info=True)
                    errors = 1 if progress["claimed"] else errors + 1
                    if errors >= MAX_CONSECUTIVE_ERRORS:
                        current_app.logger.info("Exiting process, letting container restart.")
                        self._stop.set()
                        return
                    self._stop.wait(ERROR_RETRY_SECONDS)

    def start(self, app):
        current_app.logger.info("Background tasks processor started.")
        signal.signal(signal.SIGTERM, self._release_on_shutdown)
        for task_type in TASKS.values():
            for i in range(task_type.threads):
                threading.Thread(target=self.work, args=(app, task_type), name=f"{task_type.name}-{i}", daemon=True).start()
        try:
            # threads only stop the worker after repeated errors, then the container restarts
            self._stop.wait()
        except KeyboardInterrupt:
            current_app.logger.error("Keyboard interrupt!")
            self._stop.set()
        self._release_current_tasks()
        sys.exit(1)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        BackgroundTasks().start(app)
