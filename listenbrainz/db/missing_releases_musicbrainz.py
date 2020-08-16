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


def insert_user_missing_releases_data(user_id, data):
    """ Insert missing releases data that a user has submitted to ListenBrainz but
        has not submitted to MusicBrainz in the db.

        Args:
            user_id (int): row id of the user.
            data (list): Release data that is submitted to ListenBrainz by the users
                         but is not submitted to MusicBrainz.
    """
    missing_releases_data = {
        'missing_releases': data
    }

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO missing_releases_musicbrainz (user_id, data)
                 VALUES (:user_id, :missing_releases_data)
            ON CONFLICT (user_id)
          DO UPDATE SET user_id = :user_id,
                        data = :missing_releases_data,
                        created = NOW()
            """), {
                'user_id': user_id,
                'missing_releases_data': ujson.dumps(missing_releases_data),
            }
        )


def get_user_missing_releases_data(user_id):
    """ Get missing releases data that has not been submitted to LB
        for a user with the given row ID.

        Args:
            user_id (int): the row ID of the user in the DB

        Returns:
            A dict of the following format
            {
                'user_id' (int): the row ID of the user in the DB,
                'data'  (dict): missing releases data.
                'created' (datetime): datetime object representing when the missing
                                      releases data for this user was last updated.
            }

    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, data, created
              FROM missing_releases_musicbrainz
             WHERE user_id = :user_id
            """), {
                    'user_id': user_id
                }
        )
        row = result.fetchone()
        return dict(row) if row else None
