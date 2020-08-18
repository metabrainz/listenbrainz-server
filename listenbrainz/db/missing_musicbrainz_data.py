# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2020 Vansika Pareek <vansikapareek2001@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import ujson
import sqlalchemy

from listenbrainz import db
from flask import current_app


def insert_user_missing_musicbrainz_data(user_id, data, source):
    """ Insert missing musicbrainz data that a user has submitted to ListenBrainz but
        has not submitted to MusicBrainz in the db.

        Args:
            user_id (int): row id of the user.
            data (list): Data that is submitted to ListenBrainz by the users
                         but is not submitted to MusicBrainz.
            source (str): Source of generation of missing MusicBrainz data.
    """
    missing_musicbrainz_data = {
        'missing_musicbrainz_data': data
    }

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO missing_musicbrainz_data (user_id, data, source)
                 VALUES (:user_id, :missing_musicbrainz_data, :source)
            ON CONFLICT (user_id)
          DO UPDATE SET user_id = :user_id,
                        data = :missing_musicbrainz_data,
                        source = :source,
                        created = NOW()
            """), {
                'user_id': user_id,
                'missing_musicbrainz_data': ujson.dumps(missing_musicbrainz_data),
                'source': source
            }
        )


def get_user_missing_musicbrainz_data(user_id, source):
    """ Get missing musicbrainz data that has not been submitted to LB
        for a user with the given row ID.

        Args:
            user_id (int): the row ID of the user in the DB
            source (str): Source of generation of missing MusicBrainz data.

        Returns:
            A dict of the following format
            {
                'user_id' (int): the row ID of the user in the DB,
                'missing_musicbrainz_data'  (dict): missing musicbrainz data.
                'created' (datetime): datetime object representing when the missing
                                      MusicBrainz data for this user was last updated.
            }

        A sample response from the DB would look like:
        {
            "created": "Tue, 18 Aug 2020 16:46:09 GMT",
            "data": {
                "missing_musicbrainz_data": [
                    {
                        "artist_msid": "f26d35e3-5fdd-43cf-8b94-71936451bc07",
                        "artist_name": "Welshly Arms",
                        "listened_at": "2020-04-29 23:56:23",
                        "recording_msid": "568eeea3-9255-4878-9df8-296043344e04",
                        "release_msid": "8c5ba30c-4851-48fd-ac02-1b194cdb34d1",
                        "release_name": "No Place Is Home",
                        "track_name": "How High"
                    },
                    {
                        "artist_msid": "f26d35e3-5fdd-43cf-8b94-71936451bc07",
                        "artist_name": "Welshly Arms",
                        "listened_at": "2020-04-29 23:52:16",
                        "recording_msid": "b911620d-8541-44e5-a0db-977679efb37d",
                        "release_msid": "8c5ba30c-4851-48fd-ac02-1b194cdb34d1",
                        "release_name": "No Place Is Home",
                        "track_name": "Sanctuary"
                    }
                ]
            },
            "user_id": 1
        }

    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, data, created
              FROM missing_musicbrainz_data
             WHERE user_id = :user_id
               AND source = :source
            """), {
                    'user_id': user_id,
                    'source': source
                }
        )
        row = result.fetchone()
        return dict(row) if row else None
