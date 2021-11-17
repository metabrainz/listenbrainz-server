import psycopg2
import sqlalchemy
import ujson
from flask import current_app
from psycopg2.extras import execute_values

from listenbrainz import db

def get_year_in_music(user_id):
    """ Get year in music data for requested user """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT data FROM statistics.year_in_music WHERE user_id = :user_id
        """), user_id=user_id)
        row = result.fetchone()
        return row["data"] if row else None


def insert_new_releases_of_top_artists(user_id, data):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.year_in_music (user_id, data)
                 VALUES (:user_id, jsonb_build_object('new_releases_of_top_artists', :data :: jsonb))
            ON CONFLICT (user_id)
          DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """), user_id=user_id, data=ujson.dumps(data))


def insert_most_prominent_color(data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, data)
             SELECT "user".id
                  , jsonb_build_object('most_prominent_color', color)
               FROM (VALUES %s) AS t(user_name, color)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_colors = ujson.loads(data)
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, user_colors.items())
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting most prominent colors:", exc_info=True)


def insert_similar_users(data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, data)
             SELECT "user".id
                  , jsonb_build_object('similar_users', similar_users::jsonb)
               FROM (VALUES %s) AS t(user_name, similar_users)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    similar_users = [(k, ujson.dumps(v)) for k, v in data.items()]
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, similar_users)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting similar users:", exc_info=True)
