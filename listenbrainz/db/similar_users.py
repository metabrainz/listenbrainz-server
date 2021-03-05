import time

import sqlalchemy
import psycopg2
from psycopg2.errors import OperationalError
from psycopg2.extras import execute_values
import ujson

from listenbrainz import db


ROWS_PER_BATCH = 1000

def import_user_similarities(data):
    """ Import the user similarities into the DB by inserting the data into a new table
        and then rotating the table into place atomically.
    """

    # Start by importing the data into an import table
    conn = db.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            curs.execute("""DROP TABLE IF EXISTS recommendation.similar_user_import""")
            curs.execute("""CREATE TABLE recommendation.similar_user_import  (
                                user_name     VARCHAR NOT NULL,
                                similar_users JSONB)""")
            query = "INSERT INTO recommendation.similar_user_import VALUES %s"
            values = []
            for row in data:
                user = str(list(row)[0])
                values.append((user, ujson.dumps(row[user])))
                if len(values) == ROWS_PER_BATCH:
                    execute_values(curs, query, values, template=None)
                    values = []
            execute_values(curs, query, values, template=None)

    except psycopg2.errors.OperationalError as err:
        mb_conn.rollback()
        print("Error: Cannot import user similarites: ", str(err))
        return


    # Next lookup user names and insert them into the new similar_users table
    try:
        with conn.cursor() as curs:
            curs.execute("""DROP TABLE IF EXISTS recommendation.tmp_similar_user""")
            curs.execute("""CREATE TABLE recommendation.tmp_similar_user
                                         (LIKE recommendation.similar_user
                                          EXCLUDING INDEXES
                                          EXCLUDING CONSTRAINTS)""")
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

    except psycopg2.errors.OperationalError as err:
        mb_conn.rollback()
        print("Error: Cannot correlated user similarity user name: ", str(err))
        return

    # Finally rotate the table into place
    try:
        with conn.cursor() as curs:
            curs.execute("""ALTER TABLE recommendation.similar_user
                              RENAME TO delete_similar_user""")
            curs.execute("""ALTER TABLE recommendation.tmp_similar_user
                              RENAME TO similar_user""")
    except psycopg2.errors.OperationalError as err:
        mb_conn.rollback()
        print("Error: Failed to rotate similar_users table into place: ", str(err))
        return

    # Last, delete the old table
    try:
        with conn.cursor() as curs:
            curs.execute("""DROP TABLE recommendation.delete_similar_user CASCADE""")
    except psycopg2.errors.OperationalError as err:
        mb_conn.rollback()
        print("Error: Failed to clean up old similar user table: ", str(err))
        return
