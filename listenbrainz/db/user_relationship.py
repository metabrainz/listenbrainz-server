# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2020 Param Singh <iliekcomputers@gmail.com>
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

from typing import List

from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException

import sqlalchemy

VALID_RELATIONSHIP_TYPES = (
    'follow',
)


def insert(user_0: int, user_1: int, relationship_type: str) -> None:
    if relationship_type not in VALID_RELATIONSHIP_TYPES:
        raise ValueError(f"Invalid relationship type: {relationship_type}")

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO user_relationship (user_0, user_1, relationship_type)
                 VALUES (:user_0, :user_1, :relationship_type)
        """), {
            "user_0": user_0,
            "user_1": user_1,
            "relationship_type": relationship_type,
        })


def is_following_user(follower: int, followed: int) -> bool:
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT COUNT(*) as cnt
              FROM user_relationship
             WHERE user_0 = :follower
               AND user_1 = :followed
               AND relationship_type = 'follow'
        """), {
            "follower": follower,
            "followed": followed,
        })
        return result.fetchone()['cnt'] > 0


def delete(user_0: int, user_1: int, relationship_type: str) -> None:
    if relationship_type not in VALID_RELATIONSHIP_TYPES:
        raise ValueError(f"Invalid relationship type: {relationship_type}")

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE
              FROM user_relationship
            WHERE user_0 = :user_0
              AND user_1 = :user_1
              AND relationship_type = :relationship_type
        """), {
            "user_0": user_0,
            "user_1": user_1,
            "relationship_type": relationship_type,
        })


def get_followers_of_user(user: int) -> List[dict]:
    """ Returns a list of users who follow the specified user.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT "user".musicbrainz_id AS musicbrainz_id
              FROM user_relationship
              JOIN "user"
                ON "user".id = user_0
             WHERE user_1 = :followed
               AND relationship_type = 'follow'

        """), {
            "followed": user,
        })
        return [dict(row) for row in result.fetchall()]


def get_following_for_user(user: int) -> List[dict]:
    """ Returns a list of users who the specified user follows.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT "user".musicbrainz_id AS musicbrainz_id
              FROM user_relationship
              JOIN "user"
                ON "user".id = user_1
             WHERE user_0 = :user
               AND relationship_type = 'follow'

        """), {
            "user": user,
        })
        return [dict(row) for row in result.fetchall()]
