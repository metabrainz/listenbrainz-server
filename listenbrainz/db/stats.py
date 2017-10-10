"""This module contains functions to insert and retrieve statistics
   calculated from Google BigQuery into the database.
"""

import sqlalchemy
import ujson
from listenbrainz import db


def insert_user_stats(user_id, artists, recordings, releases, artist_count):
    """Inserts user stats calculated from Google BigQuery into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id (int): the row id of the user,
             artists (dict): the top artists listened to by the user
             recordings (dict): the top recordings listened to by the user
             releases (dict): the top releases listened to by the user
             artist_count (int): the total number of artists listened to by the user
    """

    # put all artist stats into one dict which will then be inserted
    # into the artist column of the stats.user table
    artist_stats = {
        'count': artist_count,
        'all_time': artists
    }

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.user (user_id, artists, recordings, releases)
                 VALUES (:user_id, :artists, :recordings, :releases)
            ON CONFLICT (user_id)
          DO UPDATE SET artists = :artists,
                        recordings = :recordings,
                        releases = :releases,
                        last_updated = NOW()
            """), {
                'user_id': user_id,
                'artists': ujson.dumps(artist_stats),
                'recordings': ujson.dumps(recordings),
                'releases': ujson.dumps(releases)
            }
        )


def get_user_stats(user_id):
    """Get user stats for user with given ID.

        Args: user_id (int): the row ID of the user in the DB

        Returns: A dict of the following format
                 {
                    "user_id" (int): the id of the user
                    "artists" (dict): artist stats for the user
                    "releases" (dict) : release stats for the user
                    "recordings" (dict): recording stats for the user
                    "last_updated" (datetime): timestamp when the stats were last updated
                 }
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, artists, releases, recordings, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """), {
                'user_id': user_id
            }
        )
        row = result.fetchone()
        return dict(row) if row else None
