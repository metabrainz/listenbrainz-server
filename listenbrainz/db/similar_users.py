import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import psycopg2

from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException


def import_user_similarities(data):
    """ Import the user similarities into the DB by inserting the data into a new table
        and then rotating the table into place atomically.
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO user_relationship (user_0, user_1, relationship_type)
                 VALUES (:user_0, :user_1, :relationship_type)
        """), {
            "user_0": user_0,
            "user_1": user_1,
            "relationship_type": relationship_type,
        })
