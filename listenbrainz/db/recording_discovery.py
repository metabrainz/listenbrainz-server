import psycopg2
from flask import current_app
from psycopg2.extras import execute_values

from listenbrainz import db


def insert_recording_discovery(data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.recording_discovery (user_id, recording_mbid, first_listened_at, latest_listened_at)
             SELECT "user".id
                  , recording_mbid::uuid
                  , first_listened_at::timestamptz
                  , latest_listened_at::timestamptz
               FROM (VALUES %s) AS t(user_id, recording_mbid, first_listened_at, latest_listened_at)
               JOIN "user" ON "user".id = user_id -- to remove rows for users that do not exist
        ON CONFLICT DO UPDATE
                SET first_listened_at  = EXCLUDED.first_listened_at
                  , latest_listened_at = EXCLUDED.latest_listened_at
    """
    discoveries = [(x["user_id"], x["recording_mbid"], x["first_listened_at"], x["latest_listened_at"]) for x in data]
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, discoveries, page_size=5000)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting recording discoveries:", exc_info=True)
