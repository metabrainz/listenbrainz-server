import time

from flask import current_app
from sqlalchemy import text

from listenbrainz.background.delete import delete_listens_history, delete_user
from listenbrainz.background.export import export_user
from listenbrainz.webserver import create_app, db_conn, ts_conn


def add_task(user_id, task):
    """ Add a task to the background tasks """
    query = "INSERT INTO background_tasks (user_id, task) VALUES (:user_id, :task) ON CONFLICT DO NOTHING"
    db_conn.execute(text(query), {"user_id": user_id, "task": task})
    db_conn.commit()


def get_task():
    """ Fetch one task from the database """
    query = "SELECT * FROM background_tasks LIMIT 1"
    result = db_conn.execute(text(query))
    return result.first()


def remove_task(task):
    query = "DELETE FROM background_tasks WHERE id = :id"
    db_conn.execute(text(query), {"id": task.id})
    db_conn.commit()


class BackgroundTasks:

    def process_task(self, task) -> bool:
        """ Perform the task and return whether the task succeeded """
        if task.task == "delete_listens":
            delete_listens_history(db_conn, task.user_id, task.created)
        elif task.task == "delete_user":
            delete_user(db_conn, task.user_id, task.created)
        elif task.task == "export_user":
            export_user(db_conn, ts_conn, task.user_id)
        else:
            current_app.logger.error(f"Unknown task type: {task}")
        return True

    def start(self):
        current_app.logger.info("Background tasks processor started.")
        while True:
            try:
                db_conn.rollback()
                task = get_task()
                if task is None:
                    time.sleep(5)
                    continue
                status = self.process_task(task)
                if status:
                    remove_task(task)
            except KeyboardInterrupt:
                current_app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                current_app.logger.error("Error in background tasks processor:", exc_info=True)
                time.sleep(5)

if __name__ == "__main__":
    bt = BackgroundTasks()
    with create_app().app_context():
        bt.start()
