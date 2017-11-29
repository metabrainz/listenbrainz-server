"""This module contains functions to insert and retrieve statistics
   calculated from Google BigQuery into the database.
"""

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2017 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


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
            INSERT INTO statistics.user (user_id, artist, recording, release)
                 VALUES (:user_id, :artists, :recordings, :releases)
            ON CONFLICT (user_id)
          DO UPDATE SET artist = :artists,
                        recording = :recordings,
                        release = :releases,
                        last_updated = NOW()
            """), {
                'user_id': user_id,
                'artists': ujson.dumps(artist_stats),
                'recordings': ujson.dumps(recordings),
                'releases': ujson.dumps(releases)
            }
        )


def get_user_stat(user_id, stat):
    """ Get a particular stat for user with the given row ID.

        Args:
            user_id (int): the row ID of the user in the DB
            stat (str): the column name of the user stat to be retrieved

        Returns:
            A dict of the following format
            {
                'user_id' (int): the row ID of the user in the DB,
                '<stat>'  (dict): the stat requested
                'last_updated' (datetime): datetime object representing when
                                           this stat was last updated
            }
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, {stat}, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """.format(stat=stat)), {
                'user_id': user_id
            }
        )
        row = result.fetchone()
        return dict(row) if row else None


def get_user_artists(user_id):
    """Get top artists for user with given ID.

        Args:
            user_id (int): the row ID of the user in the DB

        Returns:
            A dict of the following format
            {
                'user_id' (int): the row ID of the user in the DB,
                '<stat>'  (dict): the stat requested
                'last_updated' (datetime): datetime object representing when
                                        this stat was last updated
            }
    """
    return get_user_stat(user_id, 'artist')
