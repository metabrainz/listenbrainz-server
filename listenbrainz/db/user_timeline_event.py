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
import orjson

from datetime import datetime

from listenbrainz.db.model.user_timeline_event import (
    UserTimelineEvent,
    UserTimelineEventType,
    UserTimelineEventMetadata,
    RecordingRecommendationMetadata,
    NotificationMetadata,
    HiddenUserTimelineEvent,
    PersonalRecordingRecommendationMetadata
)
from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException
from typing import List, Tuple

from listenbrainz.db.model.review import CBReviewTimelineMetadata


def create_user_timeline_event(
    user_id: int,
    event_type: UserTimelineEventType,
    metadata: UserTimelineEventMetadata,
) -> UserTimelineEvent:
    """ Creates a user timeline event in the database and returns the event.
    """
    try:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text("""
                INSERT INTO user_timeline_event (user_id, event_type, metadata)
                    VALUES (:user_id, :event_type, :metadata)
                RETURNING id, user_id, event_type, metadata, created
                """), {
                    'user_id': user_id,
                    'event_type': event_type.value,
                    'metadata': orjson.dumps(metadata.dict()).decode("utf-8"),
                }
            )

            return UserTimelineEvent(**result.mappings().first())
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


def create_user_notification_event(user_id: int, metadata: NotificationMetadata) -> UserTimelineEvent:
    """ Create a notification event in the database and returns it.
    """
    return create_user_timeline_event(
        user_id=user_id,
        event_type=UserTimelineEventType.NOTIFICATION,
        metadata=metadata
    )

def delete_user_timeline_event(
        id: int,
        user_id:int
) -> bool:
    ''' Deletes recommendation and notification event using id'''
    try:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text('''
                    DELETE FROM user_timeline_event
                    WHERE user_id = :user_id
                    AND id = :id
                '''), {
                    'user_id': user_id,
                    'id': id
                })
            return result.rowcount == 1
    except Exception as e:
        raise DatabaseException(str(e))


def create_user_cb_review_event(user_id: int, metadata: CBReviewTimelineMetadata) -> UserTimelineEvent:
    """ Creates a CritiqueBrainz review event in the database and returns it.
    """
    return create_user_timeline_event(
        user_id=user_id,
        event_type=UserTimelineEventType.CRITIQUEBRAINZ_REVIEW,
        metadata=metadata
    )


def create_personal_recommendation_event(user_id: int, metadata:
    PersonalRecordingRecommendationMetadata) -> UserTimelineEvent:
    """ Creates a personal recommendation event in the database and returns it.
        The User ID in the table is the recommender, meanwhile the users in the
        metadata key are the recommendee
    """
    try:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text("""
                INSERT INTO user_timeline_event (user_id, event_type, metadata)
                    VALUES (
                        :user_id,
                        'personal_recording_recommendation',
                        jsonb_build_object(
                            'track_name', :track_name,
                            'artist_name', :artist_name,
                            'release_name', :release_name,
                            'recording_mbid', :recording_mbid,
                            'recording_msid', :recording_msid,
                            'users', (
                                SELECT jsonb_agg("user".id) as users
                                  FROM unnest(:users) as arr
                                  INNER JOIN "user"
                                  ON "user".musicbrainz_id = arr
                            ),
                            'blurb_content', :blurb_content
                        )
                    )
                RETURNING id, user_id, event_type, metadata, created
                """), {
                    'user_id': user_id,
                    'track_name': metadata.track_name,
                    'artist_name': metadata.artist_name,
                    'release_name': metadata.release_name,
                    'recording_mbid': metadata.recording_mbid,
                    'recording_msid': metadata.recording_msid,
                    'users': metadata.users,
                    'blurb_content': metadata.blurb_content
                }
            )

            return UserTimelineEvent(**result.mappings().first())
    except Exception as e:
        raise DatabaseException(str(e))


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

        return [UserTimelineEvent(**row) for row in result.mappings()]


def get_user_track_recommendation_events(user_id: int, count: int = 50) -> List[UserTimelineEvent]:
    """ Gets track recommendation events created by the specified user.

    The optional `count` parameter can be used to control the number of events being returned.
    """
    return get_user_timeline_events(
        user_id=user_id,
        event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
        count=count,
    )


def get_recording_recommendation_events_for_feed(user_ids: Tuple[int], min_ts: float, max_ts: float, count: int) \
        -> List[UserTimelineEvent]:
    """ Gets a list of recording_recommendation events for specified users.

    user_ids is a tuple of user row IDs.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, user_id, event_type, metadata, created
              FROM user_timeline_event
             WHERE user_id IN :user_ids
               AND created > :min_ts
               AND created < :max_ts
               AND event_type = :event_type
          ORDER BY created DESC
             LIMIT :count
        """), {
            "user_ids": tuple(user_ids),
            "min_ts": datetime.utcfromtimestamp(min_ts),
            "max_ts": datetime.utcfromtimestamp(max_ts),
            "count": count,
            "event_type": UserTimelineEventType.RECORDING_RECOMMENDATION.value,
        })

        return [UserTimelineEvent(**row) for row in result.mappings()]


def get_personal_recommendation_events_for_feed(user_id: int, min_ts: int, max_ts: int, count: int) -> List[UserTimelineEvent]:
    """ Gets a list of personal_recording_recommendation events for specified users.

    user_ids is a tuple of user row IDs.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_timeline_event.id
                 , user_timeline_event.user_id
                 , user_timeline_event.event_type
                 ,
                 (
                    SELECT jsonb_build_object(
                        'track_name', user_timeline_event.metadata -> 'track_name',
                        'artist_name', user_timeline_event.metadata -> 'artist_name',
                        'release_name', user_timeline_event.metadata -> 'release_name',
                        'recording_mbid', user_timeline_event.metadata -> 'recording_mbid',
                        'recording_msid', user_timeline_event.metadata -> 'recording_msid',
                        'users', jsonb_agg("user".musicbrainz_id),
                        'blurb_content', user_timeline_event.metadata -> 'blurb_content'
                    ) AS metadata
                    FROM jsonb_array_elements_text(user_timeline_event.metadata -> 'users') AS arr
                   INNER JOIN "user" ON arr.value::int = "user".id
                 )
                 , user_timeline_event.created
                 , "user".musicbrainz_id as user_name
              FROM user_timeline_event
              JOIN "user"
                ON user_timeline_event.user_id = "user".id
             WHERE (user_timeline_event.metadata -> 'users') @> (:user_id)::text::jsonb
                OR user_timeline_event.user_id = :user_id
               AND user_timeline_event.created > :min_ts
               AND user_timeline_event.created < :max_ts
               AND user_timeline_event.event_type = :event_type
          ORDER BY user_timeline_event.created DESC
             LIMIT :count
        """), {
            "user_id": user_id,
            "min_ts": datetime.utcfromtimestamp(min_ts),
            "max_ts": datetime.utcfromtimestamp(max_ts),
            "count": count,
            "event_type": UserTimelineEventType.PERSONAL_RECORDING_RECOMMENDATION.value,
        })

        return [UserTimelineEvent(**row) for row in result.mappings()]


def get_cb_review_events(user_ids: List[int], min_ts: int, max_ts: int, count: int) -> List[UserTimelineEvent]:
    """ Gets a list of CritiqueBrainz review events for specified users.

    user_ids is a tuple of user row IDs.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, user_id, event_type, metadata, created
              FROM user_timeline_event
             WHERE user_id IN :user_ids
               AND created > :min_ts
               AND created < :max_ts
               AND event_type = :event_type
          ORDER BY created DESC
             LIMIT :count
        """), {
            "user_ids": tuple(user_ids),
            "min_ts": datetime.utcfromtimestamp(min_ts),
            "max_ts": datetime.utcfromtimestamp(max_ts),
            "count": count,
            "event_type": UserTimelineEventType.CRITIQUEBRAINZ_REVIEW.value,
        })

        return [UserTimelineEvent(**row) for row in result.mappings()]


def get_user_timeline_event_by_id(id: int) -> UserTimelineEvent:
    """ Gets timeline event by its id
        Args:
            id: row ID of the timeline event
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, user_id, event_type, metadata, created
              FROM user_timeline_event
             WHERE id = :id
        """), {
            "id": id,
        })
        row = result.mappings().first()
        return UserTimelineEvent(**row) if row else None


def get_user_notification_events(user_id: int, count: int = 50) -> List[UserTimelineEvent]:
    """ Gets notification posted on the user's timeline.

    The optional `count` parameter can be used to control the number of events being returned.
    """
    return get_user_timeline_events(
        user_id=user_id,
        event_type=UserTimelineEventType.NOTIFICATION,
        count=count
    )


def hide_user_timeline_event(user_id: int, event_type: UserTimelineEventType, event_id: int) -> bool:
    """ Adds events that are to be hidden """
    try:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text('''
                INSERT INTO hide_user_timeline_event (user_id, event_type, event_id)
                    VALUES (:user_id, :event_type, :event_id)
                ON CONFLICT (user_id, event_type, event_id)
                DO NOTHING
            '''), {
                'user_id': user_id,
                'event_type': event_type,
                'event_id': event_id
                }
            )
            return result.rowcount == 1
    except Exception as e:
        raise DatabaseException(str(e))


def get_hidden_timeline_events(user_id: int, count: int) -> List[HiddenUserTimelineEvent]:
    '''Retrieves all events that are hidden by the user, based on event_type'''
    try:
        with db.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text('''
                SELECT *
                  FROM hide_user_timeline_event
                 WHERE user_id = :user_id
              ORDER BY created DESC
                 LIMIT :count
            '''), {
                'user_id': user_id,
                'count': count
                }
            )
            return [HiddenUserTimelineEvent(**row) for row in result.mappings()]
    except Exception as e:
        raise DatabaseException(str(e))


def unhide_timeline_event(user: int, event_type: UserTimelineEventType, event_id: int) -> bool:
    ''' Deletes hidden timeline events for a user with specific row id '''
    try:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text('''
                DELETE FROM hide_user_timeline_event WHERE
                user_id = :user_id AND
                event_type = :event_type AND
                event_id = :event_id
            '''), {
                'user_id': user,
                'event_type': event_type,
                'event_id': event_id
                }
            )
            return result.rowcount == 1
    except Exception as e:
        raise DatabaseException(str(e))
