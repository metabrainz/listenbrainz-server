# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2021 Param Singh <me@param.codes>
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
import pydantic
import ujson

from data.model.user_timeline_event import UserTimelineEvent, UserTimelineEventType, UserTimelineEventMetadata, RecordingRecommendationMetadata
from enum import Enum
from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException
from typing import List


def create_user_timeline_event(
    user_id: int,
    event_type: UserTimelineEventType,
    metadata: UserTimelineEventMetadata,
) -> UserTimelineEvent:
    """ Creates a user timeline event in the database and returns the event.
    """
    try:
        with db.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text("""
                INSERT INTO user_timeline_event (user_id, event_type, metadata)
                    VALUES (:user_id, :event_type, :metadata)
                RETURNING id, user_id, event_type, metadata, created
                """), {
                    'user_id': user_id,
                    'event_type': event_type.value,
                    'metadata': ujson.dumps(metadata.dict()),
                }
            )

            r = dict(result.fetchone())
            return UserTimelineEvent(**r)
    except Exception as e:
        raise DatabaseException(str(e))


def create_user_track_recommendation_event(user_id: int, metadata: RecordingRecommendationMetadata) -> UserTimelineEvent:
    """ Creates a track recommendation event in the database and returns it.
    """
    return create_user_timeline_event(
        user_id=user_id,
        event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
        metadata=metadata,
    )

def get_user_timeline_events(user_id: int, event_type: UserTimelineEventType, count: int = 50) -> List[UserTimelineEvent]:
    """ Gets user timeline events of the specified type associated with the specified user.

    The optional `count` parameter can be used to control the number of events being returned.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, user_id, event_type, metadata, created
              FROM user_timeline_event
             WHERE user_id = :user_id
               AND event_type = :event_type
          ORDER BY created
             LIMIT :count
        """), {
            'user_id': user_id,
            'event_type': event_type.value,
            'count': count,
        })

        return [UserTimelineEvent(**row) for row in result.fetchall()]


def get_user_track_recommendation_events(user_id: int, count: int = 50) -> List[UserTimelineEvent]:
    """ Gets track recommendation events created by the specified user.

    The optional `count` parameter can be used to control the number of events being returned.
    """
    return get_user_timeline_events(
        user_id=user_id,
        event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
        count=count,
    )
