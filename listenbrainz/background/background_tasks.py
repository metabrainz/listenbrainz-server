import time

from flask import current_app
from sqlalchemy import text

from listenbrainz.background.delete import delete_listens_history, delete_user
from listenbrainz.background.export import export_user
from listenbrainz.webserver import create_app, db_conn, ts_conn
from listenbrainz.background.listens_importer import import_listens

def add_task(user_id, task):
    """ Add a task to the background tasks """
    query = "INSERT INTO background_tasks (user_id, task) VALUES (:user_id, :task) ON CONFLICT DO NOTHING"
    db_conn.execute(text(query), {"user_id": user_id, "task": task})
    db_conn.commit()


def get_task():
    """ Fetch one task from the database """
    query = "SELECT * FROM background_tasks ORDER BY created LIMIT 1 FOR UPDATE SKIP LOCKED"
    result = db_conn.execute(text(query))
    return result.first()


def remove_task(task):
    query = "DELETE FROM background_tasks WHERE id = :id"
    db_conn.execute(text(query), {"id": task.id})
    db_conn.commit()


class BackgroundTasks:

    def process_task(self, task):
        """ Perform the task """
        try:
            current_app.logger.info(f"Processing task: {task.id}")
            if task.task == "delete_listens":
                delete_listens_history(db_conn, task.user_id, task.created)
            elif task.task == "delete_user":
                delete_user(db_conn, task.user_id, task.created)
            elif task.task == "export_all_user_data":
                export_user(db_conn, ts_conn, task.user_id, task.metadata)
            elif task.task == "import_listens":
                import_listens(db_conn, ts_conn, task.user_id, task.metadata)
            else:
                current_app.logger.error(f"Unknown task type: {task}")
        except Exception:
            current_app.logger.error("Error processing task:", exc_info=True)

    def start(self):
        current_app.logger.info("Background tasks processor started.")
        while True:
            try:
                task = get_task()
                if task is None:
                    time.sleep(5)
                    continue
                self.process_task(task)
                remove_task(task)
            except KeyboardInterrupt:
                current_app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                current_app.logger.error("Error in background tasks processor:", exc_info=True)
                time.sleep(2)
                # Exit the container, restart
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
