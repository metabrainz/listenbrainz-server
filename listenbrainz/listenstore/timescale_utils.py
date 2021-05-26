import time
from collections import defaultdict
from datetime import datetime, timedelta
import psycopg2
from psycopg2.errors import UntranslatableCharacter
import sqlalchemy
import logging

from brainzutils import cache
from listenbrainz.utils import init_cache
from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT, REDIS_USER_TIMESTAMPS, DATA_START_YEAR_IN_SECONDS
from listenbrainz import config


logger = logging.getLogger(__name__)

NUM_YEARS_TO_PROCESS_FOR_CONTINUOUS_AGGREGATE_REFRESH = 3
SECONDS_IN_A_YEAR = 31536000


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
    query = 'SELECT musicbrainz_id FROM "user"'
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

    # Reset the timestamps and listen counts to 0 for all users
    for user_name in user_list:
        cache.set(REDIS_USER_LISTEN_COUNT + user_name, 0, expirein=0, encode=False)
        cache.set(REDIS_USER_LISTEN_COUNT + user_name, 0, expirein=0, encode=False)
        cache.set(REDIS_USER_TIMESTAMPS + user_name, "0,0", expirein=0)

    # Tabulate all of the listen counts/timestamps for all users
    logger.info("Scan the whole listen table...")
    listen_counts = defaultdict(int)
    user_timestamps = {}
    query = "SELECT listened_at, user_name FROM listen where created <= :ts"
    try:
        with timescale.engine.connect() as connection:
            result = connection.execute(
                sqlalchemy.text(query), ts=last_created_ts)
            for row in result:
                ts = row[0]
                user_name = row[1]
                if user_name not in user_timestamps:
                    user_timestamps[user_name] = [ts, ts]
                else:
                    if ts > user_timestamps[user_name][1]:
                        user_timestamps[user_name][1] = ts
                    if ts < user_timestamps[user_name][0]:
                        user_timestamps[user_name][0] = ts

                listen_counts[user_name] += 1

    except psycopg2.OperationalError as e:
        logger.error("Cannot query db to fetch user list." %
                     str(e), exc_info=True)
        raise

    logger.info("Setting updated cache entries.")
    # Set the timestamps and listen counts for all users
    for user_name in user_list:
        try:
            cache.increment(REDIS_USER_LISTEN_COUNT + user_name, amount=listen_counts[user_name])
        except KeyError:
            pass

        try:
            tss = cache.get(REDIS_USER_TIMESTAMPS + user_name)
            (min_ts, max_ts) = tss.split(",")
            min_ts = int(min_ts)
            max_ts = int(max_ts)
            if min_ts and min_ts < user_timestamps[user_name][0]:
                user_timestamps[user_name][0] = min_ts
            if max_ts and max_ts > user_timestamps[user_name][1]:
                user_timestamps[user_name][1] = max_ts
            cache.set(REDIS_USER_TIMESTAMPS + user_name, "%d,%d" %
                      (user_timestamps[user_name][0], user_timestamps[user_name][1]), expirein=0)
        except KeyError:
            pass


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
            self.log.error("Cannot refresh listen_count_30day cont agg: %s" %
                           str(e), exc_info=True)
            raise

        t1 = time.monotonic()
        logger.info("Refreshed continuous aggregate for: %s to %s in %.2fs" % (str(
            datetime.fromtimestamp(start_ts)), str(datetime.fromtimestamp(end_ts)), t1-t0))

        end_ts -= (NUM_YEARS_TO_PROCESS_FOR_CONTINUOUS_AGGREGATE_REFRESH * SECONDS_IN_A_YEAR)
        start_ts -= (NUM_YEARS_TO_PROCESS_FOR_CONTINUOUS_AGGREGATE_REFRESH * SECONDS_IN_A_YEAR)
        if end_ts < DATA_START_YEAR_IN_SECONDS:
            break


class TimescaleListenStoreException(Exception):
    pass
