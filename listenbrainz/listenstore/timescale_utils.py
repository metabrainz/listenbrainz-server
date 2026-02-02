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


def delete_listens():
    """ Delete listens and update counts, listen min/max timestamps """
    # Implementation Notes:
    #
    # While working on this, I encountered the following issues. These notes also explain some peculiarities of the SQL
    # queries that follow.
    #
    # 1) Delete Mismatch
    #
    # The listen_delete_metadata table holds the rows to be deleted FROM listen. We fetch the rows from it and delete
    # corresponding listens FROM listen table. After that, we update counts and timestamps in listen_user_metadata table
    # as necessary. Between the time rows are deleted FROM listen table and the time we get to clear up the
    # listen_delete_metadata table, new rows may have been inserted in the latter. So, we would have deleted rows from
    # listen_delete_metadata table without deleting the actual listens.
    #
    # This issue exists because our transaction isolation level is READ COMMITTED. This issue can be prevented by using
    # the REPEATABLE READ isolation level but that comes with its own issues. To alleviate this issue, the id
    # column has been added to the listen_delete_metadata table. Before the start of the transaction, we record the
    # maximum id in the table. This id is used to select the rows from listen_delete_metadata table and the same rows
    # are then later deleted.
    #
    # 2) "Fake/Double" Delete
    #
    # The DELETE listen endpoint does not verify whether a listen already exists in the listen table. It also does not
    # check whether that row for that delete already exists in listen_delete_metadata table. This can actually be a
    # quite common situation, for example: the user clicking delete for the same listen twice. If we count the number of
    # deleted listens to subtract using listen_delete_metadata table, the count may become inaccurate.
    #
    # Therefore, we use the RETURNING clause with the DELETE FROM listen statement to return the user_id and created
    # of the actual deletes and then calculate the deleted listen count from it and subtract it from existing count to
    # get the updated count.
    #
    # However, PG's CTEs have a limitation that they unrelated WITH'ed queries may be executed in any order and if there
    # are multiple updates to a row in a CTE, only 1 query's update will be visible afterwards. So the queries to update
    # timestamps cannot be put in the WITH of update counts query. Further, this means that we cannot utilise the
    # RETURNING clause to return listened_at for these queries and need to read the listen_delete_metadata table.
    # (**There is an alternative if needed: create a temporary table out of the RETURNING clause data.**)
    # But but wait... For updating min/max listened_at timestamp, we scan the listen table so even if there are double
    # entries or fake entries for delete, it doesn't matter. The new min/max timestamps are going to come from the
    # listen table anyway.
    #
    # 3) Interaction with regular metadata update cron job
    #
    # A periodic cron job run updates the metadata in the listen_user_metadata table. Specifically, the count,
    # min_listened_at and max_listened_at values for a user have been calculated only on the basis of listens created
    # prior to the created value of that user's listen_user_metadata row. But many users will have listens created
    # since the last cron job run, some of these may end up in deletes as well.
    #
    # Listens which have a created value later than the created value in the listen_user_metadata table haven't yet
    # been counted in the listen_user_metadata table. So when deleted the count of these listens should not be
    # subtracted from listen_user_metadata. The FILTER clause with count(*) is responsible for that.
    #
    # Similarly, a listen with listened_at greater than max_listened_at can be created later than the created value
    # in the listen_user_metadata table. If this listen is deleted and the listen with max_listened_at is also deleted,
    # max(listened_at) of deleted listens != max_listened_at of listened_user_metadata. So, we will have missed to
    # update listen timestamps in this case. To avoid this, we need to check max_listened_at is in the list of
    # listened_at of delete listens. The same situation can happen with min_listened_at.
    #
    # 4) Redundant work in updating min/max listened_at
    #
    # To update min/max listened_at fields, it doesn't really matter whether the listens were created prior or after
    # the created value in the listen_user_metadata table. It is a matter of choosing the best performance
    # characteristics. When updating the these fields we use the existing min/max listened_at values to reduce the
    # search space.
    #
    # Currently, we include the created clause as well here but I wonder if it is actually slower that way because
    # created is not included in the index on listened_at and user_id so the row needs to fetched from the table
    # for the checking the created clause. If we keep this check, we tally the min/max for listens till the created
    # value and the remaining listens with newer created values are handled by the regular update script.
    #
    # If it is determined that using created here is actually slower and we remove that clause: we'll be tallying
    # listens using just listened_at and user_id here so the newer created listens will be checked for timestamp as
    # well here. During the regular update run, we won't know which user's max_listened_at/min_listened_at already has
    # been updated and hence, will be doing redundant work. Another question is even if we did know the exact rows,
    # could we execute the update query partially.
    #
    # TODO: Check effect of using created.

    # select the maximum id in the table till now, we are only to process
    # deletes with row id earlier than this.
    select_max_id = "SELECT max(id) AS max_id FROM listen_delete_metadata"

    # count deleted listens, checked created and update listen counts
    delete_listens_and_update_listen_counts = """
        WITH deleted_listens AS (
            DELETE FROM listen l
             USING listen_delete_metadata ldm
             WHERE ldm.id <= :max_id
               AND l.user_id = ldm.user_id
               AND l.listened_at = ldm.listened_at
               AND l.recording_msid = ldm.recording_msid
               AND ldm.status = 'pending'
         RETURNING ldm.id, l.user_id, l.created
        ), update_counts AS (
            UPDATE listen_user_metadata lm
               SET count = count - deleted_count
              FROM (
                        SELECT user_id
                             , count(*) AS deleted_count
                          FROM deleted_listens dl
                      GROUP BY user_id
                   ) uc
             WHERE lm.user_id = uc.user_id
        )
            UPDATE listen_delete_metadata ldm
               SET status = 'complete'
                 , listen_created = dl.created
              FROM deleted_listens dl
             WHERE ldm.id = dl.id
    """

    # check for which users the listen of minimum listened_at was deleted, for those users
    # calculate new minimum listened_at
    update_listen_min_ts = """
        WITH update_ts AS (
            SELECT user_id, min_listened_at, lm.created
              FROM listen_delete_metadata dl
              JOIN listen_user_metadata lm
             USING (user_id)
             WHERE dl.id <= :max_id
          GROUP BY user_id, min_listened_at, lm.created
            -- check if min_listened_at is in list of listened_at of deleted listens,
            -- cannot use = min(dl.listened_at). see note 3
            HAVING min_listened_at = ANY(array_agg(dl.listened_at))
        ), calculate_new_ts AS (
            SELECT user_id
                 , new_ts.min_listened_ts AS new_listened_at
              FROM update_ts u
              -- for each user calculate the new minimum timestamp
              JOIN LATERAL (
                    SELECT min(listened_at) AS min_listened_ts
                      FROM listen l
                        -- new minimum will be greater than the last one
                     WHERE l.listened_at >= u.min_listened_at
                       AND l.user_id = u.user_id
                       AND l.created <= u.created
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
            SELECT user_id, max_listened_at, lm.created
              FROM listen_delete_metadata dl
              JOIN listen_user_metadata lm
             USING (user_id)
             WHERE dl.id <= :max_id
          GROUP BY user_id, max_listened_at, lm.created
            -- check if max_listened_at is in list of listened_at of deleted listens,
            -- cannot use = max(dl.listened_at). see note 3
            HAVING max_listened_at = ANY(array_agg(dl.listened_at))
        ), calculate_new_ts AS (
            SELECT user_id
                 , new_ts.max_listened_ts AS new_listened_at
              FROM update_ts u
                -- for each user calculate the new maximum timestamp
              JOIN LATERAL (
                    SELECT max(listened_at) AS max_listened_ts
                      FROM listen l
                        -- new maximum will be lesser than the last one
                     WHERE l.listened_at <= u.max_listened_at
                       AND l.user_id = u.user_id
                       AND l.created <= u.created
                   ) AS new_ts
                ON TRUE
        )
            UPDATE listen_user_metadata lm
               SET max_listened_at = new_listened_at
              FROM calculate_new_ts mt
             WHERE lm.user_id = mt.user_id
    """
    mark_invalid_rows_query = """
        UPDATE listen_delete_metadata
           SET status = 'invalid'
         WHERE id <= :max_id
           AND status = 'pending'
    """

    with timescale.engine.begin() as connection:
        result = connection.execute(text(select_max_id))
        row = result.fetchone()

        if not row:
            logger.info("No pending deletes")
            return

        max_id = row.max_id
        logger.info("Found max id in listen_delete_metadata table: %s", max_id)

        logger.info("Deleting Listens and updating affected listens counts")
        connection.execute(text(delete_listens_and_update_listen_counts), {"max_id": max_id})

        logger.info("Update minimum listen timestamp affected by deleted listens")
        connection.execute(text(update_listen_min_ts), {"max_id": max_id})

        logger.info("Update maximum listen timestamp affected by deleted listens")
        connection.execute(text(update_listen_max_ts), {"max_id": max_id})

        logger.info("Cleanup listen delete metadata table")
        connection.execute(text(mark_invalid_rows_query), {"max_id": max_id})

        logger.info("Completed deleting listens and updating affected metadata")


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
    """ Delete listens and update user metadata to reflect deleted listens and listens created since last run """
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
