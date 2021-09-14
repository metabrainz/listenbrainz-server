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
from typing import Optional, Union

import sqlalchemy
from data.model.sitewide_artist_stat import (SitewideArtistStat,
                                             SitewideArtistStatJson)
from data.model.user_artist_map import UserArtistMapStat, UserArtistMapStatJson
from data.model.user_daily_activity import (UserDailyActivityStat, UserDailyActivityStatRange)
from data.model.user_entity import UserEntityStat, UserEntityStatRange
from data.model.user_listening_activity import (UserListeningActivityStat, UserListeningActivityStatRange)
from flask import current_app
from listenbrainz import db
from pydantic import ValidationError


def get_timestamp_for_last_user_stats_update():
    """ Get the time when the user stats table was last updated
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT MAX(last_updated) as last_update_ts
              FROM statistics.user
            """))
        row = result.fetchone()
        return row['last_update_ts'] if row else None


def insert_user_jsonb_data(user_id: int, stats_type: str, stats: UserEntityStatRange):
    """ Inserts jsonb data into the given column

        Args:
            user_id: the row id of the user,
            stats_type: the type of entity for which to insert stats in
            stats: the data to be inserted
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.user_new (user_id, stats_type, stats_range, data, count, from_ts, to_ts, last_updated)
                 VALUES (:user_id, :stats_type, :stats_range, :data, :count, :from_ts, :to_ts, NOW())
            ON CONFLICT (user_id, stats_type, stats_range)
          DO UPDATE SET data = :data,
                        count = :count,
                        from_ts = :from_ts,
                        to_ts = :to_ts,
                        last_updated = NOW()
            """), {
            "user_id": user_id,
            "stats_type": stats_type,
            "stats_range": stats.stats_range,
            "data": stats.data.json(exclude_none=True),
            "count": stats.count,
            "from_ts": stats.from_ts,
            "to_ts": stats.to_ts
        })


def insert_user_jsonb_data_without_count(user_id, stats_type: str,
                                         stats: Union[UserListeningActivityStatRange, UserDailyActivityStatRange]):
    """Inserts listening_activity stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

        Args:
            user_id: the row id of the user
            stats_type: the type of entity for which to insert stats in
            stats: the data to be inserted
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.user_new (user_id, stats_type, stats_range, data, from_ts, to_ts, last_updated)
                 VALUES (:user_id, :stats_type, :stats_range, :data, :from_ts, :to_ts, NOW())
            ON CONFLICT (user_id, stats_type, stats_range)
          DO UPDATE SET data = :data,
                        from_ts = :from_ts,
                        to_ts = :to_ts,
                        last_updated = NOW()
            """), {
            "user_id": user_id,
            "stats_type": stats_type,
            "stats_range": stats.stats_range,
            "data": stats.data.json(exclude_none=True),
            "from_ts": stats.from_ts,
            "to_ts": stats.to_ts
        })


def _insert_sitewide_jsonb_data(stats_range: str, column: str, data: dict):
    """ Inserts jsonb data into the given column

        Args:
            stats_range: the range for which the stats have been calculated
            column: the column in the database to insert into
            data: the data to be inserted
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.sitewide (stats_range, {column})
                 VALUES (:stats_range, :data)
            ON CONFLICT (stats_range)
          DO UPDATE SET {column} = COALESCE(statistics.sitewide.{column} || :data, :data),
                        last_updated = NOW()
            """.format(column=column)), {
            'stats_range': stats_range,
            'data': json.dumps(data)
        })


def insert_user_artist_map(user_id: int, artist_map: UserArtistMapStatJson):
    """Inserts artist_map stats calculated from Spark into the database.

       If stats are already present for some user, they are updated to the new
       values passed.

       Args: user_id: the row id of the user,
             artist_map: the artist_map stats of the user
    """
    _insert_user_jsonb_data(
        user_id=user_id, column='artist_map', data=artist_map.dict(exclude_none=True))


def insert_sitewide_artists(stats_range: str, artists: SitewideArtistStatJson):
    """Inserts sitewide artist stats calculated from Spark into the database.

       If stats are already present for a time range, they are updated to the new
       values passed.

       Args: stats_range: the range for which the stats have been calculated,
             artists: the top artists for a particular stats_range
    """
    _insert_sitewide_jsonb_data(
        stats_range, column='artist', data=artists.dict(exclude_none=True))


def get_user_stats(user_id: int, stats_range: str, stats_type: str) -> Optional[UserEntityStat]:
    """ Get top stats of given type in a time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
            stats_type: the entity type to fetch stats for
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, last_updated, data, count, from_ts, to_ts, stats_range
              FROM statistics.user_new
             WHERE user_id = :user_id
             AND stats_range = :stats_range
             AND stats_type = :stats_type
            """), {
            'stats_range': stats_range,
            'user_id': user_id,
            'stats_type': stats_type,
        })
        row = result.fetchone()

    try:
        return UserEntityStat(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} top artists for user with user_id: {user_id}.
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


def get_sitewide_artists(stats_range: str) -> Optional[SitewideArtistStat]:
    """ Get sitewide top artists for from the DB.

        Args:
            stats_range: The time range for which to fetch the stats for.

        Returns:
            data: The top artists for the given time_range if they are present else None
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                SELECT stats_range, artist as data, last_updated
                  FROM statistics.sitewide
                 WHERE stats_range = :stats_range
            """), {
            'stats_range': stats_range
        })
        row = result.fetchone()

    try:
        return SitewideArtistStat(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} sitewide top artists.
                                 Data: {data}""".format(stats_range, data=json.dumps(dict(row)['data'], indent=3)), exc_info=True)


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


# TODO: Add tests for this function


def delete_sitewide_stats(stats_range: str):
    """ Delete stats for a particular time_range

        Args:
            stats_range: The stats_range for which stats should be deleted
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM statistics.sitewide
             WHERE stats_range = :stats_range
            """), {
            'stats_range': stats_range
        })
