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

from data.model.common_stat import StatRange, StatApi
from data.model.user_artist_map import UserArtistMapRecord
from data.model.user_daily_activity import UserDailyActivityRecord
from data.model.user_entity import UserEntityRecord
from data.model.user_listening_activity import UserListeningActivityRecord
from flask import current_app
from listenbrainz import db
from pydantic import ValidationError


# sitewide statistics are stored in the user statistics table
# as statistics for a special user with the following user_id
SITEWIDE_STATS_USER_ID = 15753


def get_timestamp_for_last_user_stats_update():
    """ Get the time when the user stats table was last updated
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT MAX(last_updated) as last_update_ts
              FROM statistics.user_new
            """))
        row = result.fetchone()
        return row['last_update_ts'] if row else None


def insert_user_jsonb_data(user_id: int, stats_type: str, stats: StatRange):
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


def insert_sitewide_jsonb_data(stats_type: str, stats: StatRange):
    """ Inserts jsonb data into the given column

        Args:
            stats_type: the type of entity for which to insert stats in
            stats: the data to be inserted
    """
    insert_user_jsonb_data(SITEWIDE_STATS_USER_ID, stats_type, stats)


def get_user_stats(user_id: int, stats_range: str, stats_type: str) -> Optional[StatApi[UserEntityRecord]]:
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
        return StatApi[UserEntityRecord](**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} top artists for user with user_id: {user_id}.
                                 Data: {data}""".format(stats_range=stats_range, user_id=user_id,
                                                        data=json.dumps(dict(row)[stats_range], indent=3)),
                                 exc_info=True)
        return None


def get_user_activity_stats(user_id: int, stats_range: str, stats_type: str, stats_model) -> Optional[StatApi]:
    """Get activity stats in the given time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
            stats_type: the entity type to fetch stats for
            stats_model: the pydantic model for the stats
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, last_updated, data, from_ts, to_ts, stats_range
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
        return stats_model(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting {stats_range} listening_activity for user with user_id:
                                    {user_id}. Data: {data}""".format(stats_range=stats_range, user_id=user_id,
                                                                      data=json.dumps(dict(row)[stats_range], indent=3)),
                                 exc_info=True)
        return None


def get_user_listening_activity(user_id: int, stats_range: str) -> Optional[StatApi[UserListeningActivityRecord]]:
    """Get listening activity in the given time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    return get_user_activity_stats(user_id, stats_range, 'listening_activity', StatApi[UserListeningActivityRecord])


def get_user_daily_activity(user_id: int, stats_range: str) -> Optional[StatApi[UserDailyActivityRecord]]:
    """Get daily activity in the given time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    return get_user_activity_stats(user_id, stats_range, 'daily_activity', StatApi[UserDailyActivityRecord])


def get_user_artist_map(user_id: int, stats_range: str) -> Optional[StatApi[UserArtistMapRecord]]:
    """Get artist map in the given time range for user with given ID.

        Args:
            user_id: the row ID of the user in the DB
            stats_range: the time range to fetch the stats for
    """
    return get_user_activity_stats(user_id, stats_range, 'artist_map', StatApi[UserArtistMapRecord])


def get_sitewide_stats(stats_range: str, stats_type: str) -> Optional[StatApi[UserEntityRecord]]:
    """ Get top stats of given type in a time range for user with given ID.

        Args:
            stats_range: the time range to fetch the stats for
            stats_type: the entity type to fetch stats for
    """
    return get_user_stats(SITEWIDE_STATS_USER_ID, stats_range, stats_type)


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
                  FROM statistics.user_new
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
            DELETE FROM statistics.user_new
             WHERE user_id = :user_id
            """), {
            'user_id': user_id
        })


# TODO: Add tests for this function


def delete_sitewide_stats():
    """ Delete sitewide stats """
    delete_user_stats(SITEWIDE_STATS_USER_ID)
