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


import json
from typing import Optional

import sqlalchemy
from flask import current_app
from pydantic import ValidationError
from listenbrainz import db
from data.model.user_daily_activity import (UserDailyActivityStat,
                                            UserDailyActivityStatJson)
from data.model.user_listening_activity import (UserListeningActivityStat,
                                                UserListeningActivityStatJson)
from data.model.user_artist_stat import (UserArtistStat,
                                         UserArtistStatJson)
from data.model.user_artist_map import(UserArtistMapStat,
                                       UserArtistMapStatJson)
from data.model.user_recording_stat import (UserRecordingStat,
                                            UserRecordingStatJson)
from data.model.user_release_stat import (UserReleaseStat,
                                          UserReleaseStatJson)


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


def _insert_jsonb_data(user_id: int, column: str, data: dict):
    """ Inserts jsonb data into the given column

        Args: user_id: the row id of the user,
              column: the column in database to insert into
              data: the data to be inserted
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.user (user_id, {column})
                 VALUES (:user_id, :data)
            ON CONFLICT (user_id)
          DO UPDATE SET {column} = COALESCE(statistics.user.{column} || :data, :data),
                        last_updated = NOW()
            """.format(column=column)), {
            'user_id': user_id,
            'data': json.dumps(data),
        }
        )


def insert_user_artists(user_id: int, artists: UserArtistStatJson):
    """ Inserts artist stats calculated from Spark into the database.

        If stats are already present for some user, they are updated to the new
        values passed.

        Args: user_id: the row id of the user,
              artists: the top artists listened to by the user
    """
    _insert_jsonb_data(user_id=user_id, column='artist', data=artists.dict(exclude_none=True))


def insert_user_releases(user_id: int, releases: UserReleaseStatJson):
    """Inserts release stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id: the row id of the user,
             releases: the top releases listened to by the user
    """
    _insert_jsonb_data(user_id=user_id, column='release', data=releases.dict(exclude_none=True))


def insert_user_recordings(user_id: int, recordings: UserRecordingStatJson):
    """Inserts recording stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id: the row id of the user,
             recordings: the top releases listened to by the user
    """
    _insert_jsonb_data(user_id=user_id, column='recording', data=recordings.dict(exclude_none=True))


def insert_user_listening_activity(user_id: int, listening_activity: UserListeningActivityStatJson):
    """Inserts listening_activity stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id: the row id of the user,
             listening_activity: the listening_activity stats of the user
    """
    _insert_jsonb_data(user_id=user_id, column='listening_activity', data=listening_activity.dict(exclude_none=True))


def insert_user_daily_activity(user_id: int, daily_activity: UserDailyActivityStatJson):
    """Inserts daily_activity stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id: the row id of the user,
             daily_activity: the daily_activity stats of the user
    """
    _insert_jsonb_data(user_id=user_id, column='daily_activity', data=daily_activity.dict(exclude_none=True))


def insert_user_artist_map(user_id: int, artist_map: UserArtistMapStatJson):
    """Inserts artist_map stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id: the row id of the user,
             artist_map: the artist_map stats of the user
    """
    _insert_jsonb_data(user_id=user_id, column='artist_map', data=artist_map.dict(exclude_none=True))


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


def get_user_artists(user_id: int, stats_range: str) -> Optional[UserArtistStat]:
    """Get top artists in a time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, artist->:range AS {range}, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """.format(range=stats_range)), {
            'range': stats_range,
            'user_id': user_id
        })
        row = result.fetchone()

    try:
        return UserArtistStat(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} top artists for user with user_id: {user_id}.
                                 Data: {data}""".format(stats_range=stats_range, user_id=user_id,
                                                        data=json.dumps(dict(row)[stats_range], indent=3)),
                                 exc_info=True)
        return None


def get_user_releases(user_id: int, stats_range: str) -> Optional[UserReleaseStat]:
    """Get top releases in a time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, release->:range AS {range}, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """.format(range=stats_range)), {
            'range': stats_range,
            'user_id': user_id
        })
        row = result.fetchone()

    try:
        return UserReleaseStat(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} top releases for user with user_id: {user_id}.
                                 Data: {data}""".format(stats_range=stats_range, user_id=user_id,
                                                        data=json.dumps(dict(row)[stats_range], indent=3)),
                                 exc_info=True)
        return None


def get_user_recordings(user_id: int, stats_range: str) -> Optional[UserRecordingStat]:
    """Get top recordings in a time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, recording->:range AS {range}, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """.format(range=stats_range)), {
            'range': stats_range,
            'user_id': user_id
        })
        row = result.fetchone()

    try:
        return UserRecordingStat(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} top recordings for user with user_id: {user_id}.
                                 Data: {data}""".format(stats_range=stats_range, user_id=user_id,
                                                        data=json.dumps(dict(row)[stats_range], indent=3)),
                                 exc_info=True)
        return None


def get_user_listening_activity(user_id: int, stats_range: str) -> Optional[UserListeningActivityStat]:
    """Get listening activity in the given time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, listening_activity->:range AS {range}, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """.format(range=stats_range)), {
            'range': stats_range,
            'user_id': user_id
        })
        row = result.fetchone()

    try:
        return UserListeningActivityStat(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} listening_activity for user with user_id:
                                    {user_id}. Data: {data}""".format(stats_range=stats_range, user_id=user_id,
                                                                      data=json.dumps(dict(row)[stats_range], indent=3)),
                                 exc_info=True)
        return None


def get_user_daily_activity(user_id: int, stats_range: str) -> Optional[UserDailyActivityStat]:
    """Get daily activity in the given time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, daily_activity->:range AS {range}, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """.format(range=stats_range)), {
            'range': stats_range,
            'user_id': user_id
        })
        row = result.fetchone()

    try:
        return UserDailyActivityStat(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} daily_activity for user with user_id: {user_id}.
                                 Data: {data}""".format(stats_range=stats_range, user_id=user_id,
                                                        data=json.dumps(dict(row)[stats_range], indent=3)),
                                 exc_info=True)
        return None


def get_user_artist_map(user_id: int, stats_range: str) -> Optional[UserArtistMapStat]:
    """Get artist map in the given time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, artist_map->:range AS {range}, last_updated
              FROM statistics.user
             WHERE user_id = :user_id
            """.format(range=stats_range)), {
            'range': stats_range,
            'user_id': user_id
        })
        row = result.fetchone()

    try:
        return UserArtistMapStat(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} artist_map for user with user_id: {user_id}.
                                 Data: {data}""".format(stats_range=stats_range, user_id=user_id,
                                                        data=json.dumps(dict(row)[stats_range], indent=3)),
                                 exc_info=True)
        return None


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
