"""This module contains functions to insert and retrieve statistics
   calculated from Apache Spark into the database.
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

def get_timestamp_for_last_user_stats_update():
    """ Get the time when the user stats table was last updated
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT MAX(last_updated) as last_update_ts
              FROM statistics.user
            """
        ))
        row = result.fetchone()
        return row['last_update_ts'] if row else None


def insert_user_stats(user_id, artists, recordings, releases, artist_count):
    """Inserts user stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id (int): the row id of the user,
             artists (dict): the top artists listened to by the user
             recordings (dict): the top recordings listened to by the user
             releases (dict): the top releases listened to by the user
             artist_count (int): the total number of artists listened to by the user
    """

    artist_stats = {
        'count': artist_count,
        'all_time': {
            'artists': artists,
        }
    }

    recording_stats = {
        'all_time': {
            'recordings': recordings,
        },
    }


    release_stats = {
        'all_time': {
            'releases': releases,
        }
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
                'recordings': ujson.dumps(recording_stats),
                'releases': ujson.dumps(release_stats),
            }
        )


def get_user_stats(user_id, columns):
    """ Get a particular stat for user with the given row ID.

        Args:
            user_id (int): the row ID of the user in the DB
            columns (str): the column name(s) of the user stat to be retrieved

        Returns:
            A dict of the following format
            {
                'user_id' (int): the row ID of the user in the DB,
                '<stat>'  (dict): the stats requested, for better description see below
                'last_updated' (datetime): datetime object representing when
                                           this stat was last updated
            }

            The `stat` dict contains all stats calculated by Apache Spark stored in that column
            from listenbrainz.stats.user, keyed by stat name.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, {columns}, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """.format(columns=columns)), {
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
                'artist'  (dict): artist stats for the user, see below for better description
                'last_updated' (datetime): datetime object representing when
                                        this stat was last updated
            }


            the `artist` dict will be of the following format:
            {
                'all_time': all time artist listen counts for the user
                            calculated by listenbrainz.stats.user.get_top_artists
                'count': the total number of artists this user has listened to
                                calculated by listenbrainz.stats.user.get_artist_count
            }

            In general, the `artist` dict will contain all artist related stats
            calculated for the user in listenbrainz.stats.user, keyed by stat name.
    """
    return get_user_stats(user_id, 'artist')


def get_all_user_stats(user_id):
    """ Get ALL user stats for user with given ID.

        Args:
            user_id (int): the row ID of the user in the DB

        Returns:
            A dict of the following format
            {
                'user_id' (int): the row ID of the user in the DB
                'artist' (dict): artist stats for the user, for description see below
                'recording' (dict): recording stats for the user, for description see below
                'release' (dict): release stats for the user, for description see below
                'last_updated': datetime object representing when these stats were
                                last updated
            }


            The artist dict contains all artist related stats calculated for the user
            from listenbrianz.stats.user

            Similarly, the recording and release dicts contain all recording and release
            related stats calculated for the user keyed by stat name.
    """

    return get_user_stats(user_id, 'artist, recording, release')


def valid_stats_exist(user_id, days):
    """ Returns True if statistics for a user have been calculated in
    the last X days (where x is passed to the function), and are present in the db

    Args:
        user_id (int): the row ID of the user
        days (int): the number of days in which stats should have been calculated
            to consider them valid

    Returns:
        bool value signifying if valid stats exist for the user in the db
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                SELECT user_id
                  FROM statistics.user
                 WHERE user_id = :user_id
                   AND last_updated >= NOW() - INTERVAL ':x days'
            """), {
                'user_id': user_id,
                'x': days,
            })
        row = result.fetchone()
        return True if row is not None else False


def delete_user_stats(user_id):
    """ Delete stats for user with the given row ID.
        Args:
            user_id (int): the row ID of the user in the DB
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM statistics.user
             WHERE user_id = :user_id
            """), {
                'user_id': user_id
            })
