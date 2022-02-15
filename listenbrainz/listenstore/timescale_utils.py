import logging
import subprocess
from datetime import datetime

import psycopg2
import sqlalchemy
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import timescale

logger = logging.getLogger(__name__)

SECONDS_IN_A_YEAR = 31536000


def delete_listens_update_stats():
    # count deleted listens, checked created and update listen counts
    delete_listens_and_update_listen_counts = """
        WITH deleted_listens AS (
            DELETE FROM listen l
             USING listen_delete_metadata ldm
             WHERE ldm.created < :created
               AND l.user_id = ldm.user_id
               AND l.listened_at = ldm.listened_at
               AND l.data -> 'track_metadata' -> 'additional_info' ->> 'recording_msid' = ldm.recording_msid::text
         RETURNING l.user_id, l.created
           ), update_counts AS (
            SELECT user_id
                 -- count only listens which were created earlier than the the existing count high
                 -- watermark in listen metadata table
                 , count(*) FILTER (WHERE dl.created < lm.created) AS deleted_count
              FROM deleted_listens dl
              JOIN listen_user_metadata lm
             USING (user_id)
          GROUP BY user_id
        ) 
            UPDATE listen_user_metadata lm
               SET count = count - deleted_count
              FROM update_counts uc
             WHERE lm.user_id = uc.user_id
    """

    # check for which users the listen of minimum listened_at was deleted, for those users
    # calculate new minimum listened_at
    update_listen_min_ts = """
        WITH update_ts AS (
            SELECT user_id, min_listened_at
              FROM listen_delete_metadata dl
              JOIN listen_user_metadata lm
             USING (user_id)
          GROUP BY user_id, min_listened_at
            HAVING min(dl.listened_at) = min_listened_at
        ), calculate_new_ts AS (
            SELECT user_id
                 , new_ts.min_listened_ts AS new_listened_at
              FROM update_ts u
              JOIN LATERAL (
                    SELECT min(listened_at) AS min_listened_ts
                      FROM listen l
                     WHERE l.user_id = u.user_id
                       -- new minimum will be greater than the last one
                       AND l.listened_at >= u.min_listened_at
                   ) AS new_ts
                ON TRUE
        )
            UPDATE listen_user_metadata lm
               SET min_listened_at = new_listened_at
              FROM calculate_new_ts mt
             WHERE lm.user_id = mt.user_id
    """

    # check for which users the listen of maximum listened_at was deleted, for those users
    # calculate new maximum listened_at
    update_listen_max_ts = """
        WITH update_ts AS (
            SELECT user_id, max_listened_at
              FROM listen_delete_metadata dl
              JOIN listen_user_metadata lm
             USING (user_id)
          GROUP BY user_id, max_listened_at
            HAVING max(dl.listened_at) = max_listened_at
        ), calculate_new_ts AS (
            SELECT user_id
                 , new_ts.max_listened_ts AS new_listened_at
              FROM update_ts u
              JOIN LATERAL (
                    SELECT max(listened_at) AS max_listened_ts
                      FROM listen l
                     WHERE l.user_id = u.user_id
                       -- new maximum will be lesser than the last one
                       AND l.listened_at <= u.max_listened_at
                   ) AS new_ts
                ON TRUE
        )
            UPDATE listen_user_metadata lm
               SET max_listened_at = new_listened_at
              FROM calculate_new_ts mt
             WHERE lm.user_id = mt.user_id
    """
    delete_user_metadata = "DELETE FROM listen_delete_metadata WHERE created < :created"

    with timescale.engine.begin() as connection:
        created = datetime.now()

        logger.info("Deleting Listens and updating affected listens counts")
        connection.execute(text(delete_listens_and_update_listen_counts), created=created)

        logger.info("Update minimum listen timestamp affected by deleted listens")
        connection.execute(text(update_listen_min_ts))

        logger.info("Update maximum listen timestamp affected by deleted listens")
        connection.execute(text(update_listen_max_ts))

        logger.info("Clean up delete user metadata table")
        connection.execute(text(delete_user_metadata), created=created)


def update_user_listen_data():
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
    query = 'SELECT id FROM "user"'
    try:
        with db.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query))
            user_list = [row["id"] for row in result]
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


class TimescaleListenStoreException(Exception):
    pass
