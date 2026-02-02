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

from datetime import datetime, timezone
from typing import List, Iterable

import sqlalchemy

VALID_RELATIONSHIP_TYPES = (
    'follow',
)


def insert(db_conn, user_0: int, user_1: int, relationship_type: str) -> None:
    if relationship_type not in VALID_RELATIONSHIP_TYPES:
        raise ValueError(f"Invalid relationship type: {relationship_type}")

    db_conn.execute(sqlalchemy.text("""
        INSERT INTO user_relationship (user_0, user_1, relationship_type)
             VALUES (:user_0, :user_1, :relationship_type)
        ON CONFLICT (user_0, user_1, relationship_type)
         DO NOTHING
    """), {
        "user_0": user_0,
        "user_1": user_1,
        "relationship_type": relationship_type,
    })
    db_conn.commit()


def is_following_user(db_conn, follower: int, followed: int) -> bool:
    result = db_conn.execute(sqlalchemy.text("""
        SELECT COUNT(*) as cnt
          FROM user_relationship
         WHERE user_0 = :follower
           AND user_1 = :followed
           AND relationship_type = 'follow'
    """), {
        "follower": follower,
        "followed": followed,
    })
    return result.fetchone().cnt > 0


def multiple_users_by_username_following_user(db_conn, followed: int, followers: List[str]):
    ''' returns a dictionary, keys being usernames values being boolean '''
    result = db_conn.execute(sqlalchemy.text("""
        SELECT "user".musicbrainz_id,
               bool(
                   coalesce((
                    SELECT 't'
                      FROM user_relationship
                     WHERE user_1 = :followed
                       AND user_0 = "user".id
                       AND relationship_type = 'follow'
                   ), 'f')
               )
            AS result
          FROM unnest(:followers) as arr
         INNER JOIN "user"
            ON "user".musicbrainz_id = arr
    """), {
        "followers": followers,
        "followed": followed,
    })
    return {row.musicbrainz_id: row.result for row in result.fetchall()}


def delete(db_conn, user_0: int, user_1: int, relationship_type: str) -> None:
    if relationship_type not in VALID_RELATIONSHIP_TYPES:
        raise ValueError(f"Invalid relationship type: {relationship_type}")

    db_conn.execute(sqlalchemy.text("""
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
    db_conn.commit()


def get_followers_of_user(db_conn, user: int) -> List[dict]:
    """ Returns a list of users who follow the specified user.
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT "user".musicbrainz_id AS musicbrainz_id, "user".id as id
          FROM user_relationship
          JOIN "user"
            ON "user".id = user_0
         WHERE user_1 = :followed
           AND relationship_type = 'follow'

    """), {"followed": user})
    return result.mappings().all()


def get_following_for_user(db_conn, user: int) -> List[dict]:
    """ Returns a list of users who the specified user follows.
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT "user".musicbrainz_id AS musicbrainz_id, "user".id as id
          FROM user_relationship
          JOIN "user"
            ON "user".id = user_1
         WHERE user_0 = :user
           AND relationship_type = 'follow'
    """), {
        "user": user,
    })
    return result.mappings().all()


def get_follow_events(db_conn, user_ids: Iterable[int], min_ts: float, max_ts: float, count: int) -> List[dict]:
    """ Gets a list of follow events for specified users.

    Args:
        db_conn: database connection
        user_ids: is a tuple of user row IDs.

    Returns:
         a list of dicts of the following format:

            {
                user_name_0: str,
                user_name_1: str,
                created: datetime,
            }
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT follower.musicbrainz_id as user_name_0, followed.musicbrainz_id as user_name_1, ur.created
          FROM user_relationship ur
          JOIN "user" follower ON ur.user_0 = follower.id
          JOIN "user" followed ON ur.user_1 = followed.id
         WHERE ur.user_0 IN :user_ids
           AND ur.created > :min_ts
           AND ur.created < :max_ts
      ORDER BY created DESC
         LIMIT :count
    """), {
        "user_ids": tuple(user_ids),
        "min_ts": datetime.fromtimestamp(min_ts, timezone.utc),
        "max_ts": datetime.fromtimestamp(max_ts, timezone.utc),
        "count": count
    })

    return result.mappings().all()
