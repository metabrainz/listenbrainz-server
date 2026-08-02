from operator import itemgetter
import time

import psycopg2
import orjson
from brainzutils.mail import send_mail
from flask import current_app, render_template
from psycopg2.sql import SQL, Identifier
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.spark.spark_dataset import DatabaseDataset


class _SimilarUsersDataset(DatabaseDataset):
    """ Store the similar users data generated in spark into the ListenBrainz database.

    The dataset is received in chunks: a start message creates a temporary table, multiple data
    messages insert the user similarities into it and an end message swaps the temporary table into
    place atomically. See listenbrainz.spark.spark_dataset.DatabaseDataset for details.
    """

    def __init__(self):
        super().__init__("similar_users", "similar_user", "recommendation")

    def get_engine(self):
        # the similar_user table lives in the main ListenBrainz database, not timescale
        return db.engine

    def get_table(self):
        return """
            CREATE TABLE {table} (
                user_id         INTEGER NOT NULL,
                similar_users   JSONB,
                last_updated    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """

    def get_indices(self):
        return [
            "CREATE UNIQUE INDEX user_id_ndx_similar_user_{suffix} ON {table} (user_id)"
        ]

    def get_inserts(self, message):
        query = "INSERT INTO {table} (user_id, similar_users) VALUES %s"
        values = [
            (entry["user_id"], orjson.dumps(entry["similar_users"]).decode("utf-8"))
            for entry in message["data"]
        ]
        return query, None, values

    def run_post_processing(self, cursor, message):
        # spark may report users that no longer exist in the database (deleted since the run started).
        # remove them before adding the foreign key so that the constraint can be validated.
        cursor.execute(
            SQL('DELETE FROM {table} WHERE user_id NOT IN (SELECT id FROM "user")')
            .format(table=self._get_table_name())
        )
        # give the constraint a unique name so that we don't have to deal with constraint renaming
        # when the table is rotated into place.
        constraint = Identifier(f"similar_user_user_id_foreign_key_{int(time.time())}")
        cursor.execute(
            SQL("""ALTER TABLE {table}
                       ADD CONSTRAINT {constraint}
                        FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE""")
            .format(table=self._get_table_name(), constraint=constraint)
        )


SimilarUsersDataset = _SimilarUsersDataset()


def get_top_similar_users(db_conn, count: int = 200):
    """
        Fetch the count top similar users and return a tuple(user1, user2, score(0.0-1.0))
        If global_similarity is True, the return the user similarity on a global (not
        per user) scale.
    """
    similar_users = {}
    try:
        result = db_conn.execute(text("""
            SELECT u.musicbrainz_id AS user_name
                 , ou.musicbrainz_id AS other_user_name
                 , value AS similarity -- first element of array is similarity, second is global_similarity
              FROM recommendation.similar_user r 
              JOIN jsonb_each(r.similar_users) j
                ON TRUE
              JOIN "user" ou
                ON j.key::int = ou.id  -- user_name of other user stored in jsonb
              JOIN "user" u
               ON r.user_id = u.id -- user_name of the user_id stored directly in column
        """))
        while True:
            row = result.fetchone()
            if not row:
                break
            user = row.user_name
            other_user = row.other_user_name
            similarity = "%.3f" % row.similarity
            if user < other_user:
                similar_users[user + other_user] = (user, other_user, similarity)
            else:
                similar_users[other_user + user] = (other_user, user, similarity)
    except psycopg2.OperationalError as err:
        current_app.logger.error("Error: Failed to fetch top similar users %s" % str(err))
        return []

    similar_users = [similar_users[u] for u in similar_users]
    return sorted(similar_users, key=itemgetter(2), reverse=True)[:count]
