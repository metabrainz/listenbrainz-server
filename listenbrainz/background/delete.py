from datetime import datetime, timedelta

from brainzutils import cache

from data.model.external_service import ExternalServiceType
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT
from listenbrainz.db import user as db_user, listens as listens_db, listens_importer
from listenbrainz.webserver.listens_cache import invalidate_user_listen_caches
from listenbrainz.background.registry import task


def delete_user(db_conn, user_id: int, created: datetime):
    """ Delete an account and its listens DB history.

    Args:
        user_id: the LB row ID of the user
        created: listens created before this timestamp are deleted
    """
    listens_db.delete_user(user_id, created, delete_metadata=True)

    db_user.delete(db_conn, user_id)
    db_conn.commit()


def delete_listens_history(db_conn, user_id: int, created: datetime):
    """ Delete a user's history in the listens DB and retain its deletion record.

    Args:
        user_id: the LB row ID of the user
        created: listens created before this timestamp are deleted
    """
    listens_db.delete_user(user_id, created)
    cache.delete(REDIS_USER_LISTEN_COUNT + str(user_id))
    invalidate_user_listen_caches(user_id)
    listens_importer.update_latest_listened_at(db_conn, user_id, ExternalServiceType.LASTFM, 0)
    db_conn.commit()


# a delete must not be dropped because a database was down for a while: retried hourly for about a week
DELETE_MAX_ATTEMPTS = 168


@task("delete_user", threads=2, max_attempts=DELETE_MAX_ATTEMPTS, timeout=timedelta(minutes=30))
def delete_user_task(db_conn, listens_conn, task_row):
    delete_user(db_conn, task_row.user_id, task_row.created)


@task("delete_listens", threads=2, max_attempts=DELETE_MAX_ATTEMPTS, timeout=timedelta(minutes=30))
def delete_listens_task(db_conn, listens_conn, task_row):
    delete_listens_history(db_conn, task_row.user_id, task_row.created)
