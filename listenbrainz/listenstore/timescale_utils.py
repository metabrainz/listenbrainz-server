from datetime import datetime, timedelta
import psycopg2
import sqlalchemy
import subprocess
import logging

from brainzutils import cache
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz.utils import init_cache
from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_TIMESTAMPS
from listenbrainz import config


logger = logging.getLogger(__name__)

SECONDS_IN_A_YEAR = 31536000


def update_user_listen_counts():
    query = """
        WITH nm AS (
            SELECT l.user_id, count(*) as count
              FROM listen l
              JOIN listen_user_metadata lm
             USING (user_id)
             WHERE l.created > lm.created
               AND l.created <= :until
          GROUP BY l.user_id
        )
            UPDATE listen_user_metadata om
               SET count = om.count + nm.count
                 , created = :until
              FROM nm
             WHERE om.user_id = nm.user_id
    """
    # There is something weird going on here, I do not completely understand why but using engine.connect instead
    # of engine.begin causes the changes to not be persisted. Reading up on sqlalchemy transaction handling etc.
    # it makes sense that we need begin for an explicit transaction but how CRUD statements work fine with connect
    # in remaining LB is beyond me then.
    with timescale.engine.begin() as connection:
        logger.info("Starting to update listen counts")
        connection.execute(text(query), until=datetime.now())
        logger.info("Completed updating listen counts")


def add_missing_to_listen_users_metadata():
    """ Fetch users from LB and add an entry those users which are missing from listen_user_metadata """
    # Select a list of users
    user_list = []
    query = 'SELECT id FROM "user"'
    try:
        with db.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query))
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

    timescale.init_db_connection(config.SQLALCHEMY_TIMESCALE_URI)
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    init_cache(host=config.REDIS_HOST, port=config.REDIS_PORT,
               namespace=config.REDIS_NAMESPACE)

    # Find the created timestamp of the last listen
    query = "SELECT max(created) FROM listen WHERE created > :date"
    try:
        with timescale.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(
                query), date=datetime.now() - timedelta(weeks=4))
            row = result.fetchone()
            last_created_ts = row[0]
    except psycopg2.OperationalError as e:
        logger.error("Cannot query ts to fetch latest listen." %
                     str(e), exc_info=True)
        raise

    logger.info("Last created timestamp: " + str(last_created_ts))

    # Select a list of users
    user_list = []
    query = 'SELECT id FROM "user"'
    try:
        with db.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query))
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
          DO UPDATE
                SET count = 0
                  , min_listened_at = NULL
                  , max_listened_at = NULL
                  , created = 'epoch'
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

    # Reset the timestamps to 0 for all users
    for user_id in user_list:
        cache.set(REDIS_USER_TIMESTAMPS + str(user_id), "0,0", expirein=0)

    # Tabulate all of the listen timestamps for all users
    logger.info("Scan the whole listen table...")
    user_timestamps = {}
    query = "SELECT listened_at, user_id FROM listen where created <= :ts"
    try:
        with timescale.engine.connect() as connection:
            result = connection.execute(
                sqlalchemy.text(query), ts=last_created_ts)
            for row in result:
                ts = row[0]
                user_id = row[1]
                if user_id not in user_timestamps:
                    user_timestamps[user_id] = [ts, ts]
                else:
                    if ts > user_timestamps[user_id][1]:
                        user_timestamps[user_id][1] = ts
                    if ts < user_timestamps[user_id][0]:
                        user_timestamps[user_id][0] = ts
    except psycopg2.OperationalError as e:
        logger.error("Cannot query db to fetch user list." %
                     str(e), exc_info=True)
        raise

    logger.info("Setting updated cache entries.")
    # Set the timestamps for all users
    for user_id in user_list:
        try:
            tss = cache.get(REDIS_USER_TIMESTAMPS + str(user_id))
            (min_ts, max_ts) = tss.split(",")
            min_ts = int(min_ts)
            max_ts = int(max_ts)
            if min_ts and min_ts < user_timestamps[user_id][0]:
                user_timestamps[user_id][0] = min_ts
            if max_ts and max_ts > user_timestamps[user_id][1]:
                user_timestamps[user_id][1] = max_ts
            cache.set(REDIS_USER_TIMESTAMPS + str(user_id), "%d,%d" %
                      (user_timestamps[user_id][0], user_timestamps[user_id][1]), expirein=0)
        except KeyError:
            pass


def unlock_cron():
    """ Unlock the cron container """

    # Unlock the cron container
    try:
        subprocess.run(["/usr/local/bin/python", "admin/cron_lock.py", "unlock-cron", "cont-agg"])
    except subprocess.CalledProcessError as err:
        logger.error("Cannot unlock cron after updating continuous aggregates: %s" % str(err))


class TimescaleListenStoreException(Exception):
    pass
