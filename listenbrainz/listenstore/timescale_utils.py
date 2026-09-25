import logging
import subprocess
from datetime import datetime

import psycopg2
import sqlalchemy
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import listens as listens_db, timescale

logger = logging.getLogger(__name__)

SECONDS_IN_A_YEAR = 31536000


def delete_listens():
    """Process pending deletions in the listens database, retaining their history."""
    listens_db.delete_pending_listens()


def update_user_listen_data():
    """ Scan listens created since last run and update metadata in listen_user_metadata accordingly """
    query = """
        WITH new AS (
            SELECT user_id
                 , count(*) as count
                 , min(listened_at) AS min_listened_at
                 , max(listened_at) AS max_listened_at
              FROM listen l
              JOIN listen_user_metadata lm
             USING (user_id)
             WHERE l.created > lm.created
               AND l.created <= :until
          GROUP BY user_id
        )
        UPDATE listen_user_metadata old
           SET count = old.count + new.count
             , min_listened_at = least(old.min_listened_at, new.min_listened_at)
             , max_listened_at = greatest(old.max_listened_at, new.max_listened_at)
             , created = :until
          FROM new
         WHERE old.user_id = new.user_id
    """
    # There is something weird going on here, I do not completely understand why but using engine.connect instead
    # of engine.begin causes the changes to not be persisted. Reading up on sqlalchemy transaction handling etc.
    # it makes sense that we need begin for an explicit transaction but how CRUD statements work fine with connect
    # in remaining LB is beyond me then.
    with timescale.engine.begin() as connection:
        logger.info("Starting to update listen counts")
        connection.execute(text(query), {"until": datetime.now()})
        logger.info("Completed updating listen counts")


def delete_listens_and_update_user_listen_data():
    """Process listens DB deletions and refresh Timescale metadata for new listens."""
    delete_listens()
    update_user_listen_data()


def add_missing_to_listen_users_metadata():
    """ Fetch users from LB and add an entry those users which are missing from listen_user_metadata """
    # Select a list of users
    user_list = []
    query = 'SELECT id FROM "user"'
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text(query))
            for row in result:
                user_list.append(row[0])
    except psycopg2.OperationalError as e:
        logger.error("Cannot query db to fetch user list." %
                     str(e), exc_info=True)
        raise

    logger.info("Fetched %d users. Setting empty cache entries." %
                len(user_list))

    query = """
        INSERT INTO listen_user_metadata (user_id, count, min_listened_at, max_listened_at, created)
             VALUES %s
        ON CONFLICT (user_id)
         DO NOTHING
    """
    values = [(user_id, ) for user_id in user_list]
    template = "(%s, 0, NULL, NULL, 'epoch')"
    connection = timescale.engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, values, template=template)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        logger.error("Error while resetting created timestamps:", exc_info=True)
        raise


def recalculate_all_user_data():
    """ Recalculate entire listen user metadata from scratch """
    query = 'SELECT id FROM "user"'
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text(query))
            user_list = [row.id for row in result]
    except psycopg2.OperationalError:
        logger.error("Cannot query db to fetch user list", exc_info=True)
        raise

    logger.info("Fetched %d users. Resetting created timestamps for all users.", len(user_list))

    query = """
        INSERT INTO listen_user_metadata (user_id, count, min_listened_at, max_listened_at, created)
             VALUES %s
        ON CONFLICT (user_id)
          DO UPDATE
                SET count = 0
                  , min_listened_at = NULL
                  , max_listened_at = NULL
                  , created = 'epoch'
    """
    values = [(user_id,) for user_id in user_list]
    template = "(%s, 0, NULL, NULL, 'epoch')"
    connection = timescale.engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, values, template=template)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        logger.error("Error while resetting created timestamps:", exc_info=True)
        raise

    try:
        update_user_listen_data()
    except psycopg2.OperationalError as e:
        logger.error("Cannot update user data:", exc_info=True)
        raise


def unlock_cron():
    """ Unlock the cron container """

    # Unlock the cron container
    try:
        subprocess.run(["/usr/local/bin/python", "admin/cron_lock.py", "unlock-cron", "cont-agg"])
    except subprocess.CalledProcessError as err:
        logger.error("Cannot unlock cron after updating continuous aggregates: %s" % str(err))


def refresh_top_manual_mappings():
    """ Refresh top manual msid-mbid mappings view """
    with timescale.engine.connect() as ts_conn:
        ts_conn.execute(text("REFRESH MATERIALIZED VIEW mbid_manual_mapping_top"))


class TimescaleListenStoreException(Exception):
    pass
