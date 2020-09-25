"""This module contains functions to insert and retrieve recommendations
   generated from Apache Spark into the database.
"""

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2020 MetaBrainz Foundation Inc.
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


import ujson
import sqlalchemy

from listenbrainz import db
from flask import current_app
from pydantic import ValidationError

from data.model.user_cf_recommendations_recording_message import (UserRecommendationsData,
                                                                  UserRecommendationsJson)

def get_timestamp_for_last_recording_recommended():
    """ Get the time when recommendation_cf_recording table was last updated
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT MAX(created) as created_ts
              FROM recommendation.cf_recording
            """)
        )
        row = result.fetchone()
        return row['created_ts'] if row else None


def insert_user_recommendation(user_id: int, recommendations: UserRecommendationsJson):
    """ Insert recommended recording for a user in the db.

        Args:
            user_id (int): row id of the user.
            recommendations (dict): User recommendations.
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO recommendation.cf_recording (user_id, recording_mbid)
                 VALUES (:user_id, :recommendation)
            ON CONFLICT (user_id)
          DO UPDATE SET user_id = :user_id,
                        recording_mbid = :recommendation,
                        created = NOW()
            """), {
                'user_id': user_id,
                'recommendation': ujson.dumps(recommendations.dict()),
            }
        )


def get_user_recommendation(user_id):
    """ Get recommendations for a user with the given row ID.

        Args:
            user_id (int): the row ID of the user in the DB

        Returns:
            A dict of the following format
            {
                'user_id' (int): the row ID of the user in the DB,
                'recording_mbid'  (dict): recommended recording mbids
                'created' (datetime): datetime object representing when
                                      the recommendation for this user was last updated.
            }

            recording_mbid = {
                'top_artist_recording': [],
                'similar_artist_recording': []
            }
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, recording_mbid, created
              FROM recommendation.cf_recording
             WHERE user_id = :user_id
            """), {
                    'user_id': user_id
                }
        )
        row = result.fetchone()

    try:
        return UserRecommendationsData(**dict(row)) if row else None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting recommendations for user with user_id: {user_id}. Data: {data}"""
                                 .format(user_id=user_id, data=ujson.dumps(dict(row)['recording_mbid'], indent=4)), exc_info=True)
        return None
