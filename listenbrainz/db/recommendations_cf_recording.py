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


import sqlalchemy

from listenbrainz import db
from flask import current_app

def get_timestamp_for_last_recording_recommended():
    """ Get the time when recommendation_cf_recording table was last updated
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT MAX(created) as created_ts
              FROM recommendation.cf_recording
            """
        ))
        row = result.fetchone()
        return row['created_ts'] if row else None

def insert_user_recommendation(user_id, recording_mbid, artist_type=None):
    """ Insert recommended recording for a user in the db.
    """
    if artist_type is None:
        current_app.logger.critical('artist type for recommendation not specified')
        return

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO recommendation.cf_recording (user_id, recording_mbid, type)
                 VALUES (:user_id, :recording_mbid, :artist_type)
        """), {
                'user_id': user_id,
                'recording_mbid': recording_mbid,
                'artist_type': artist_type,
        }
    )
