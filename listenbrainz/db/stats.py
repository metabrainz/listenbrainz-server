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
from listenbrainz.utils import safely_import_config
safely_import_config()

def insert_user_stats(user_id, artists, recordings, releases, artist_count, yearmonth):
    """Inserts user stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id (int): the row id of the user,
             artists (dict): the top artists listened to by the user
             recordings (dict): the top recordings listened to by the user
             releases (dict): the top releases listened to by the user
             artist_count (int): the total number of artists listened to by the user
             yearmonth (str): a string representing the month in which the stats were calculated, 
                        for example '2019-01'
    """

    artist_stats = {
        'count': artist_count,
        'top_month': {
            'artists': artists,
            'month': yearmonth,
        }
    }

    recording_stats = {
        'top_month': {
            'recordings': recordings,
            'month': yearmonth,
        },
    }


    release_stats = {
        'top_month': {
            'releases': releases,
            'month': yearmonth,
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

            The `stat` dict contains all stats calculated by Google BigQuery stored in that column
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


def valid_stats_exist(user_id):
    """ Returns True if statistics for a user have been calculated in
    the last week, and are present in the db

    Args:
        user_id (int): the row ID of the user

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
                'x': config.STATS_CALCULATION_INTERVAL,
            })
        row = result.fetchone()
        return True if row is not None else False
