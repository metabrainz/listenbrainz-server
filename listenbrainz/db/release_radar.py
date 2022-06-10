import psycopg2
import sqlalchemy
from flask import current_app
from psycopg2.extras import execute_values

from listenbrainz import db


def insert_release_radar_data(data):
    """ Insert the given release radar data into the database """
    query = """
        INSERT INTO recommendation.release_radar (user_id, data, last_updated)
             SELECT "user".id
                  , data::jsonb
                  , NOW()
               FROM (VALUES %s) AS t(user_id, data)
               -- this JOIN serves no other purpose than to filter out users for whom stats were calculated but
               -- no longer exist in LB. if we don't filter, we'll get a FK conflict when such a case occurs
               JOIN "user" ON "user".id = user_id 
        ON CONFLICT (user_id)
      DO UPDATE SET data = EXCLUDED.data
                  , last_updated = EXCLUDED.last_updated
    """
    values = [(x["user_id"], x["data"]) for x in data]
    connection = db.engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, values)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting release radar data:", exc_info=True)


def get_release_radar_data(user_id):
    """ Get the release radar data for the given user """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, last_updated, data
              FROM recommendation.release_radar
             WHERE user_id = :user_id
             """), user_id=user_id)
        row = result.fetchone()
        return dict(**row) if row else None
