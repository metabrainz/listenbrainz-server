from operator import itemgetter
import time

import sqlalchemy
import psycopg2
from psycopg2.errors import OperationalError
from psycopg2.extras import execute_values
import ujson
from flask import current_app

from listenbrainz import db


ROWS_PER_BATCH = 1000


def import_user_similarities(data):
    """ Import the user similarities into the DB by inserting the data into a new table
        and then rotating the table into place atomically.

        Returns a tuple of three values:
            (user_count, avr_similar_users_per_user, error)
        If an error occurs rotating the tables in place, error will be a non-empty
        string and the user count values will be 0. Upon success error will be empty
        and the user count values will be set accordingly.
    """

    user_count = 0
    target_user_count = 0
    # Start by importing the data into an import table
    conn = db.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            curs.execute(
                """DROP TABLE IF EXISTS recommendation.similar_user_import""")
            curs.execute("""CREATE TABLE recommendation.similar_user_import  (
                                user_name     VARCHAR NOT NULL,
                                similar_users JSONB)""")
            query = "INSERT INTO recommendation.similar_user_import VALUES %s"
            values = []
            for user, similar in data.items():
                values.append((user, ujson.dumps(similar)))
                user_count += 1
                target_user_count += len(similar.keys())
                if len(values) == ROWS_PER_BATCH:
                    execute_values(curs, query, values, template=None)
                    values = []
            execute_values(curs, query, values, template=None)
        conn.commit()

    except psycopg2.errors.OperationalError as err:
        conn.rollback()
        current_app.logger.error(
            "Error: Cannot import user similarites: %s" % str(err))
        return (0, 0.0, "Error: Cannot import user similarites: %s" % str(err))

    # Next lookup user names and insert them into the new similar_users table
    try:
        with conn.cursor() as curs:
            curs.execute(
                """DROP TABLE IF EXISTS recommendation.tmp_similar_user""")
            curs.execute("""CREATE TABLE recommendation.tmp_similar_user
                                         (LIKE recommendation.similar_user
                                          EXCLUDING INDEXES
                                          EXCLUDING CONSTRAINTS
                                          INCLUDING DEFAULTS)""")
            curs.execute("""INSERT INTO recommendation.tmp_similar_user
                                        SELECT id AS user_id, similar_users
                                          FROM recommendation.similar_user_import
                                          JOIN "user"
                                            ON user_name = musicbrainz_id""")

            curs.execute("""DROP TABLE recommendation.similar_user_import""")

            # Give each constraint a unique name so that we don't have to deal with PITA constraint renaming
            curs.execute("""CREATE UNIQUE INDEX user_id_ndx_similar_user_%s
                                             ON recommendation.tmp_similar_user (user_id)""" % int(time.time()))
            curs.execute("""ALTER TABLE recommendation.tmp_similar_user
                         ADD CONSTRAINT similar_user_user_id_foreign_key_%s
                            FOREIGN KEY (user_id)
                             REFERENCES "user" (id)
                              ON DELETE CASCADE""" % int(time.time()))
        conn.commit()

    except psycopg2.errors.OperationalError as err:
        conn.rollback()
        current_app.logger.error(
            "Error: Cannot correlate user similarity user name: %s" % str(err))
        return (0, 0.0, "Error: Cannot correlate user similarity user name: %s" % str(err))

    # Finally rotate the table into place
    try:
        with conn.cursor() as curs:
            curs.execute("""ALTER TABLE recommendation.similar_user
                              RENAME TO delete_similar_user""")
            curs.execute("""ALTER TABLE recommendation.tmp_similar_user
                              RENAME TO similar_user""")
        conn.commit()
    except psycopg2.errors.OperationalError as err:
        conn.rollback()
        current_app.logger.error(
            "Error: Failed to rotate similar_users table into place: %s" % str(err))
        return (0, 0.0, "Error: Failed to rotate similar_users table into place: %s" % str(err))

    # Last, delete the old table
    try:
        with conn.cursor() as curs:
            curs.execute(
                """DROP TABLE recommendation.delete_similar_user CASCADE""")
        conn.commit()

    except psycopg2.errors.OperationalError as err:
        conn.rollback()
        current_app.logger.error(
            "Error: Failed to clean up old similar user table: %s" % str(err))
        return (0, 0.0, "Error: Failed to clean up old similar user table: %s" % str(err))

    return (user_count, target_user_count / user_count, "")


def get_top_similar_users(count=200, global_similarity=False):
    """
        Fetch the count top similar users and return a tuple(user1, user2, score(0.0-1.0))
        If global_similarity is True, the return the user similarity on a global (not
        per user) scale.
    """

    col_index = 0
    if global_similarity:
        col_index = 1

    similar_users = {}
    conn = db.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            curs.execute("""SELECT musicbrainz_id AS user_name, similar_users
                             FROM  recommendation.similar_user su
                              JOIN "user" u
                                ON user_id = u.id""")

            for row in curs.fetchall():
                user_name = row[0]
                for other_user in row[1]:
                    if user_name < other_user:
                        similar_users[user_name + other_user] = (user_name, other_user, "%.3f" % row[1][other_user][col_index])
                    else:
                        similar_users[other_user + user_name] = (other_user, user_name, "%.3f" % row[1][other_user][col_index])

    except psycopg2.errors.OperationalError as err:
        current_app.logger.error("Error: Failed to fetch top similar users %s" % str(err))
        return []

    similar_users = [similar_users[u] for u in similar_users]
    return sorted(similar_users, key=itemgetter(2), reverse=True)[:count]
