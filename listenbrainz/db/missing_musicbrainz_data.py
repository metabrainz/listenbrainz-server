# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2020 MetaBrainz Foundation Inc.
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

import orjson
import sqlalchemy

from listenbrainz import db
from pydantic import ValidationError

from data.model.user_missing_musicbrainz_data import (UserMissingMusicBrainzData,
                                                      UserMissingMusicBrainzDataJson, UserMissingMusicBrainzDataRecord)
from flask import current_app

from listenbrainz.db.mbid_manual_mapping import check_manual_mapping_exists


def insert_user_missing_musicbrainz_data(db_conn, user_id: int,
                                         missing_musicbrainz_data: UserMissingMusicBrainzDataJson, source: str):
    """ Insert missing musicbrainz data that a user has submitted to ListenBrainz but
        has not submitted to MusicBrainz in the db.

        Args:
            db_conn: database connection
            user_id : row id of the user.
            data : Data that is submitted to ListenBrainz by the users
                   but is not submitted to MusicBrainz.
            source : Source of generation of missing MusicBrainz data.
    """
    db_conn.execute(sqlalchemy.text("""
        INSERT INTO missing_musicbrainz_data (user_id, data, source)
             VALUES (:user_id, :missing_musicbrainz_data, :source)
        ON CONFLICT (user_id)
      DO UPDATE SET user_id = :user_id,
                    data = :missing_musicbrainz_data,
                    source = :source,
                    created = NOW()
        """), {
            'user_id': user_id,
            'missing_musicbrainz_data': orjson.dumps(missing_musicbrainz_data.dict()).decode("utf-8"),
            'source': source
        }
    )
    db_conn.commit()


def get_user_missing_musicbrainz_data(db_conn, ts_conn, user_id: int, source: str):
    """ Get missing musicbrainz data that has not been submitted to LB
        for a user with the given row ID.

        Args:
            db_conn: database connection
            ts_conn: timescale database connection
            user_id: the row ID of the user in the DB
            source : Source of generation of missing MusicBrainz data.

        Returns:
            A tuple of the following format
            (
                'missing_musicbrainz_data'  (dict): missing musicbrainz data,
                'created' (datetime): datetime object representing when the missing
                                      MusicBrainz data for this user was last updated.
            )

        A sample response would look like:
            ([
                {
                    "artist_name": "Katty Peri"
                    "listened_at": 1588204593,
                    "recording_msid": "568eeea3-9255-4878-9df8-296043344e04",
                    "release_name": "No Place Is Home",
                    "track_name": "How High"
                },
                {
                    "artist_name": "Welshly Arms",
                    "listened_at": 1588204583,
                    "recording_msid": "b911620d-8541-44e5-a0db-977679efb37d",
                    "release_name": "No Place Is Home",
                    "track_name": "Sanctuary"
                }
            ], datetime.datetime(2020, 5, 1, 10, 0, 0))

    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT user_id, data, created
          FROM missing_musicbrainz_data
         WHERE user_id = :user_id
           AND source = :source
        """), {
                'user_id': user_id,
                'source': source
            }
    )
    row = result.mappings().first()

    try:
        if row:
            missing_mb_data = UserMissingMusicBrainzDataJson(missing_musicbrainz_data=row["data"]["missing_musicbrainz_data"]).missing_musicbrainz_data
            if missing_mb_data:
                return remove_mapped_mb_data(ts_conn, user_id, missing_mb_data), row["created"]
        else:
            return None, None
    except ValidationError:
        current_app.logger.error("""ValidationError when getting missing musicbrainz data for source "{source}"
                                 for user with user_id: {user_id}. Data: {data}""".format(source=source, user_id=user_id,
                                 data=orjson.dumps(row['data'], option=orjson.OPT_INDENT_2)), exc_info=True)
        return None, None


def remove_mapped_mb_data(ts_conn, user_id: int, missing_musicbrainz_data: list[UserMissingMusicBrainzDataRecord]):
    """ Remove musicbrainz data that has been mapped to MusicBrainz by the user.

        Args:
            ts_conn: timescale database connection
            user_id: LB user id.
            missing_musicbrainz_data: List of missing musicbrainz data.

        Returns:
            List of missing musicbrainz data that has not been mapped to MusicBrainz.
    """
    missing_data_map = {r.recording_msid: r for r in missing_musicbrainz_data}
    existing_mappings = check_manual_mapping_exists(ts_conn, user_id, missing_data_map.keys())

    remaining_data = []
    for item in missing_musicbrainz_data:
        if item.recording_msid not in existing_mappings:
            remaining_data.append(item.dict())

    return remaining_data
