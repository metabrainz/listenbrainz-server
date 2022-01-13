from datetime import datetime, timedelta
import psycopg2
import sqlalchemy
import subprocess
import logging

from brainzutils import cache
from sqlalchemy import text

from listenbrainz.utils import init_cache
from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_TIMESTAMPS
from listenbrainz import config


logger = logging.getLogger(__name__)

SECONDS_IN_A_YEAR = 31536000


def update_user_listen_counts():
    timescale.init_db_connection(config.SQLALCHEMY_TIMESCALE_URI)
    # TODO: Check if doing existing users once and new users separately is more performant
    query = """
    WITH nc AS (
        SELECT l.user_id, count(*) as count
          FROM listen l
          JOIN listen_count lc on l.user_id = lc.user_id
         WHERE created > lc.timestamp
           AND created <= :until
      GROUP BY l.user_id
    )
    UPDATE listen_count oc
       SET count = oc.count + nc.count
         , timestamp = :until
      FROM nc
     WHERE oc.user_id = nc.user_id;
    """
    with timescale.engine.connect() as connection:
        connection.execute(text(query), until=datetime.now())

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
    query = 'SELECT musicbrainz_id, id FROM "user"'
    try:
        with db.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query))
            for row in result:
                user_list.append((row[0], row[1]))
    except psycopg2.OperationalError as e:
        logger.error("Cannot query db to fetch user list." %
                     str(e), exc_info=True)
        raise

    logger.info("Fetched %d users. Setting empty cache entries." %
                len(user_list))

    # Reset the timestamps and listen counts to 0 for all users
    for user_name, user_id in user_list:
        cache.set(REDIS_USER_LISTEN_COUNT + user_name, 0, expirein=0, encode=False)
        cache.set(REDIS_USER_TIMESTAMPS + str(user_id), "0,0", expirein=0)

    # Tabulate all of the listen counts/timestamps for all users
    logger.info("Scan the whole listen table...")
    user_timestamps = {}
    query = "SELECT listened_at, user_name, user_id FROM listen where created <= :ts"
    try:
        with timescale.engine.connect() as connection:
            result = connection.execute(
                sqlalchemy.text(query), ts=last_created_ts)
            for row in result:
                ts = row[0]
                user_id = row[2]
                if user_id not in user_timestamps:
                    user_timestamps[user_id] = [ts, ts]
                else:
                    if ts > user_timestamps[user_id][1]:
                        user_timestamps[user_id][1] = ts
                    if ts < user_timestamps[user_id][0]:
                        user_timestamps[user_id][0] = ts

                user_name = row[1]
                if user_name not in user_timestamps:
                    user_timestamps[user_name] = [ts, ts]
                else:
                    if ts > user_timestamps[user_name][1]:
                        user_timestamps[user_name][1] = ts
                    if ts < user_timestamps[user_name][0]:
                        user_timestamps[user_name][0] = ts

    except psycopg2.OperationalError as e:
        logger.error("Cannot query db to fetch user list." %
                     str(e), exc_info=True)
        raise

    logger.info("Setting updated cache entries.")
    # Set the timestamps and listen counts for all users
    for user_name, user_id in user_list:
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
