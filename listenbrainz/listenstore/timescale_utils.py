import time
from collections import defaultdict
from datetime import datetime, timedelta
import psycopg2
from psycopg2.errors import UntranslatableCharacter
import sqlalchemy
import subprocess
import logging

from brainzutils import cache
from listenbrainz.utils import init_cache
from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT, REDIS_USER_TIMESTAMPS, \
    DATA_START_YEAR_IN_SECONDS, REDIS_USER_LISTEN_COUNT_UPDATER_TS
from listenbrainz import config


logger = logging.getLogger(__name__)

NUM_YEARS_TO_PROCESS_FOR_CONTINUOUS_AGGREGATE_REFRESH = 3
SECONDS_IN_A_YEAR = 31536000


def update_user_listen_counts():
    timescale.init_db_connection(config.SQLALCHEMY_TIMESCALE_URI)
    # TODO: Check if doing existing users once and new users separately is more performant
    query = """
    WITH nc AS (
        SELECT l.user_name, count(*) as count
          FROM listen l
          JOIN listen_count lc on l.user_name = lc.user_name
         WHERE listened_at > lc.timestamp
           AND listened_at <= :until
      GROUP BY l.user_name
    )
    UPDATE listen_count oc
       SET count = oc.count + nc.count
         , timestamp = :until
      FROM nc
     WHERE oc.user_name = nc.user_name;
    """
    with timescale.engine.connect() as connection:
        until = int(datetime.now().timestamp())
        connection.execute(sqlalchemy.text(query), until=until)
        cache.set(REDIS_USER_LISTEN_COUNT_UPDATER_TS, until, expirein=0)

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
    listen_counts = defaultdict(int)
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
                listen_counts[user_name] += 1

    except psycopg2.OperationalError as e:
        logger.error("Cannot query db to fetch user list." %
                     str(e), exc_info=True)
        raise

    logger.info("Setting updated cache entries.")
    # Set the timestamps and listen counts for all users
    for user_name, user_id in user_list:
        try:
            cache.increment(REDIS_USER_LISTEN_COUNT + user_name, amount=listen_counts[user_name])
        except KeyError:
            pass

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


def refresh_listen_count_aggregate():
    """
        Manually refresh the listen_count continuous aggregate.

        Arg:

          year_offset: How many years into the past should we start refreshing (e.g 1 year,
                       will refresh everything that is 1 year or older.
          year_count: How many years from year_offset should we update.

        Example:

           Assuming today is 2022-01-01 and this function is called for year_offset 1 and
           year_count 1 then all of 2021 will be refreshed.
    """

    # Lock the cron container
    try:
        subprocess.run(["/usr/local/bin/python", "admin/cron_lock.py", "lock-cron", "cont-agg", "Updating continuous aggregates"])
    except subprocess.CalledProcessError as err:
        logger.error("Cannot lock cron for updating continuous aggregates: %s" % str(err))
        sys.exit(-1)

    logger.info("Starting to refresh continuous aggregates:")
    timescale.init_db_connection(config.SQLALCHEMY_TIMESCALE_URI)

    end_ts = int(datetime.now().timestamp()) - SECONDS_IN_A_YEAR
    start_ts = end_ts - \
        (NUM_YEARS_TO_PROCESS_FOR_CONTINUOUS_AGGREGATE_REFRESH * SECONDS_IN_A_YEAR) + 1

    while True:
        query = "call refresh_continuous_aggregate('listen_count_30day', :start_ts, :end_ts)"
        t0 = time.monotonic()
        try:
            with timescale.engine.connect() as connection:
                connection.connection.set_isolation_level(0)
                connection.execute(sqlalchemy.text(query), {
                    "start_ts": start_ts,
                    "end_ts": end_ts
                })
        except psycopg2.OperationalError as e:
            logger.error("Cannot refresh listen_count_30day cont agg: %s" % str(e), exc_info=True)
            unlock_cron()
            raise

        t1 = time.monotonic()
        logger.info("Refreshed continuous aggregate for: %s to %s in %.2fs" % (str(
            datetime.fromtimestamp(start_ts)), str(datetime.fromtimestamp(end_ts)), t1-t0))

        end_ts -= (NUM_YEARS_TO_PROCESS_FOR_CONTINUOUS_AGGREGATE_REFRESH * SECONDS_IN_A_YEAR)
        start_ts -= (NUM_YEARS_TO_PROCESS_FOR_CONTINUOUS_AGGREGATE_REFRESH * SECONDS_IN_A_YEAR)
        if end_ts < DATA_START_YEAR_IN_SECONDS:
            break

    unlock_cron()


class TimescaleListenStoreException(Exception):
    pass
