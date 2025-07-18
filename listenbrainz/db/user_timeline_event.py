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

from datetime import datetime, timezone

from sqlalchemy import text

from listenbrainz.db.model.user_timeline_event import (
    UserTimelineEvent,
    UserTimelineEventType,
    UserTimelineEventMetadata,
    ThanksMetadata,
    ThanksEventMetadata,
    RecordingRecommendationMetadata,
    NotificationMetadata,
    HiddenUserTimelineEvent,
    PersonalRecordingRecommendationMetadata, WritePersonalRecordingRecommendationMetadata
)
from listenbrainz.db.exceptions import DatabaseException
from typing import List, Iterable

from listenbrainz.db.model.review import CBReviewTimelineMetadata


def create_user_timeline_event(
    db_conn,
    user_id: int,
    event_type: UserTimelineEventType,
    metadata: UserTimelineEventMetadata,
) -> UserTimelineEvent:
    """ Creates a user timeline event in the database and returns the event.
    """
    try:
        result = db_conn.execute(text("""
            INSERT INTO user_timeline_event (user_id, event_type, metadata)
                VALUES (:user_id, :event_type, :metadata)
            RETURNING id, user_id, event_type, metadata, created
            """), {
                'user_id': user_id,
                'event_type': event_type.value,
                'metadata': orjson.dumps(metadata.dict()).decode("utf-8"),
            }
        )
        db_conn.commit()
        return UserTimelineEvent(**result.mappings().first())
    except Exception as e:
        raise DatabaseException(str(e))


def create_user_track_recommendation_event(db_conn, user_id: int, metadata: RecordingRecommendationMetadata) -> UserTimelineEvent:
    """ Creates a track recommendation event in the database and returns it.
    """
    return create_user_timeline_event(
        db_conn,
        user_id=user_id,
        event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
        metadata=metadata
    )


def create_user_notification_event(db_conn, user_id: int, metadata: NotificationMetadata) -> UserTimelineEvent:
    """ Create a notification event in the database and returns it.
    """
    return create_user_timeline_event(
        db_conn,
        user_id=user_id,
        event_type=UserTimelineEventType.NOTIFICATION,
        metadata=metadata
    )


def create_thanks_event(db_conn, thanker_id: int, thanker_username: str, thankee_id: int, thankee_username: str, metadata: ThanksMetadata) -> UserTimelineEvent:
    """ Creates a thanks event in the database and returns it.
    """
    event_metadata = dict(metadata)
    event_metadata["thanker_id"] = thanker_id
    event_metadata["thanker_username"] = thanker_username
    event_metadata["thankee_id"] = thankee_id
    event_metadata["thankee_username"] = thankee_username
    event_metadata = ThanksEventMetadata(**event_metadata)
    return create_user_timeline_event(
        db_conn,
        user_id=thanker_id,
        event_type=UserTimelineEventType.THANKS,
        metadata=event_metadata
    )


def delete_user_timeline_event(db_conn, id: int, user_id: int) -> bool:
    """ Deletes recommendation and notification event using id """
    try:
        result = db_conn.execute(sqlalchemy.text('''
                DELETE FROM user_timeline_event
                WHERE user_id = :user_id
                AND id = :id
            '''), {
                'user_id': user_id,
                'id': id
            })
        db_conn.commit()
        return result.rowcount == 1
    except Exception as e:
        raise DatabaseException(str(e))


def create_user_cb_review_event(db_conn, user_id: int, metadata: CBReviewTimelineMetadata) -> UserTimelineEvent:
    """ Creates a CritiqueBrainz review event in the database and returns it.
    """
    return create_user_timeline_event(
        db_conn,
        user_id=user_id,
        event_type=UserTimelineEventType.CRITIQUEBRAINZ_REVIEW,
        metadata=metadata
    )


def create_personal_recommendation_event(db_conn, user_id: int, metadata: WritePersonalRecordingRecommendationMetadata)\
        -> UserTimelineEvent:
    """ Creates a personal recommendation event in the database and returns it.
        The User ID in the table is the recommender, meanwhile the users in the
        metadata key are the recommendee
    """
    try:
        result = db_conn.execute(text("""
            INSERT INTO user_timeline_event (user_id, event_type, metadata)
                VALUES (
                    :user_id,
                    'personal_recording_recommendation',
                    jsonb_build_object(
                        'recording_mbid', :recording_mbid,
                        'recording_msid', :recording_msid,
                        'users', (
                            SELECT jsonb_agg("user".id ORDER BY idx) as users
                              FROM unnest(:users) WITH ORDINALITY as arr (value, idx)
                        INNER JOIN "user"
                                ON "user".musicbrainz_id = value
                        ),
                        'blurb_content', :blurb_content
                    )
                )
            RETURNING id, user_id, event_type, metadata, created
            """), {
                'user_id': user_id,
                'recording_mbid': metadata.recording_mbid,
                'recording_msid': metadata.recording_msid,
                'users': metadata.users,
                'blurb_content': metadata.blurb_content
            }
        )
        db_conn.commit()
        return UserTimelineEvent(**result.mappings().first())
    except Exception as e:
        raise DatabaseException(str(e))


def get_user_timeline_events(
    db_conn,
    user_ids: Iterable[int],
    event_type: UserTimelineEventType,
    min_ts: float,
    max_ts: float,
    count: int = 50
) -> List[UserTimelineEvent]:
    """ Gets user timeline events of the specified type associated with the specified user.

    The optional `count` parameter can be used to control the number of events being returned. The min_ts and max_ts
    can be used to influence the time period during which the events should be returned.
    """
    result = db_conn.execute(sqlalchemy.text("""
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
        "min_ts": datetime.fromtimestamp(min_ts, timezone.utc),
        "max_ts": datetime.fromtimestamp(max_ts, timezone.utc),
        "event_type": event_type.value,
        "count": count,
    })

    return [UserTimelineEvent(**row) for row in result.mappings()]


def get_recording_recommendation_events_for_feed(db_conn, user_ids: Iterable[int], min_ts: int, max_ts: int, count: int) \
        -> List[UserTimelineEvent]:
    """ Gets a list of recording_recommendation events for specified users.

    user_ids is a tuple of user row IDs.
    """
    return get_user_timeline_events(
        db_conn,
        user_ids=user_ids,
        event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
        min_ts=min_ts,
        max_ts=max_ts,
        count=count
    )


def get_personal_recommendation_events_for_feed(db_conn, user_id: int, min_ts: int, max_ts: int, count: int) -> List[UserTimelineEvent]:
    """ Gets a list of personal_recording_recommendation events for specified users.

    user_ids is a tuple of user row IDs.
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT user_timeline_event.id
             , user_timeline_event.user_id
             , user_timeline_event.event_type
             , (
                SELECT jsonb_build_object(
                            'recording_mbid', user_timeline_event.metadata->'recording_mbid',
                            'recording_msid', user_timeline_event.metadata->'recording_msid',
                            'users', COALESCE(jsonb_agg("user".musicbrainz_id ORDER BY idx), '[]'::jsonb),
                            'blurb_content', user_timeline_event.metadata->'blurb_content'
                        ) AS metadata
                  FROM jsonb_array_elements_text(user_timeline_event.metadata->'users') WITH ORDINALITY AS arr (value, idx)
            INNER JOIN "user" 
                    ON arr.value::int = "user".id
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
        "min_ts": datetime.fromtimestamp(min_ts, timezone.utc),
        "max_ts": datetime.fromtimestamp(max_ts, timezone.utc),
        "count": count,
        "event_type": UserTimelineEventType.PERSONAL_RECORDING_RECOMMENDATION.value,
    })

    return [UserTimelineEvent(
        id=row.id,
        user_id=row.user_id,
        user_name=row.user_name,
        event_type=row.event_type,
        metadata=PersonalRecordingRecommendationMetadata(**row.metadata),
        created=row.created
    ) for row in result]

def get_thanks_events_for_feed(db_conn, user_id: int, min_ts: int, max_ts: int, count: int) -> List[UserTimelineEvent]:
    """ Gets a list of thanks events for specified users.

    user_id is a tuple of user row IDs.
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT user_timeline_event.id,
               user_timeline_event.user_id,
               user_timeline_event.event_type,
               user_timeline_event.metadata,
               user_timeline_event.created,
               "user".musicbrainz_id as user_name
          FROM user_timeline_event
          INNER JOIN "user"
            ON user_timeline_event.user_id = "user".id 
         WHERE (
               (user_timeline_event.metadata -> 'users') @> to_jsonb(array[:user_id])
               OR user_timeline_event.user_id = :user_id
               OR (user_timeline_event.metadata ->> 'thankee_id')::int = :user_id
         )
           AND user_timeline_event.created > :min_ts
           AND user_timeline_event.created < :max_ts
           AND user_timeline_event.event_type = :event_type
      ORDER BY user_timeline_event.created DESC
         LIMIT :count
    """), {
        "user_id": user_id,
        "min_ts": datetime.fromtimestamp(min_ts, timezone.utc),
        "max_ts": datetime.fromtimestamp(max_ts, timezone.utc),
        "count": count,
        "event_type": UserTimelineEventType.THANKS.value,
    })
    
    return [UserTimelineEvent(
        id=row.id,
        user_id=row.user_id,
        user_name=row.user_name,
        event_type=row.event_type,
        metadata=ThanksEventMetadata(**row.metadata),
        created=row.created
    ) for row in result]


def get_cb_review_events(db_conn, user_ids: List[int], min_ts: int, max_ts: int, count: int) -> List[UserTimelineEvent]:
    """ Gets a list of CritiqueBrainz review events for specified users.

    user_ids is a tuple of user row IDs.
    """
    return get_user_timeline_events(
        db_conn,
        user_ids=user_ids,
        event_type=UserTimelineEventType.CRITIQUEBRAINZ_REVIEW,
        min_ts=min_ts,
        max_ts=max_ts,
        count=count
    )


def get_user_timeline_event_by_id(db_conn, id: int) -> UserTimelineEvent:
    """ Gets timeline event by its id
        Args:
            id: row ID of the timeline event
    """
    result = db_conn.execute(text("""
        SELECT id, user_id, event_type, metadata, created
          FROM user_timeline_event
         WHERE id = :id
    """), {
        "id": id,
    })
    row = result.mappings().first()
    return UserTimelineEvent(**row) if row else None


def get_user_notification_events(db_conn, user_ids: Iterable[int], min_ts: int, max_ts: int, count: int)\
        -> List[UserTimelineEvent]:
    """ Gets notification posted on the user's timeline.

    The optional `count` parameter can be used to control the number of events being returned.
    """
    return get_user_timeline_events(
        db_conn,
        user_ids=user_ids,
        event_type=UserTimelineEventType.NOTIFICATION,
        min_ts=min_ts,
        max_ts=max_ts,
        count=count
    )


def hide_user_timeline_event(db_conn, user_id: int, event_type: UserTimelineEventType, event_id: int) -> bool:
    """ Adds events that are to be hidden """
    try:
        result = db_conn.execute(text('''
            INSERT INTO hide_user_timeline_event (user_id, event_type, event_id)
                VALUES (:user_id, :event_type, :event_id)
            ON CONFLICT (user_id, event_type, event_id)
            DO NOTHING
        '''), {
            'user_id': user_id,
            'event_type': event_type,
            'event_id': event_id
        })
        db_conn.commit()
        return result.rowcount == 1
    except Exception as e:
        raise DatabaseException(str(e))


def get_hidden_timeline_events(db_conn, user_id: int, count: int) -> List[HiddenUserTimelineEvent]:
    '''Retrieves all events that are hidden by the user, based on event_type'''
    try:
        result = db_conn.execute(text('''
            SELECT *
              FROM hide_user_timeline_event
             WHERE user_id = :user_id
          ORDER BY created DESC
             LIMIT :count
        '''), {
            'user_id': user_id,
            'count': count
        })
        return [HiddenUserTimelineEvent(**row) for row in result.mappings()]
    except Exception as e:
        raise DatabaseException(str(e))


def unhide_timeline_event(db_conn, user: int, event_type: UserTimelineEventType, event_id: int) -> bool:
    ''' Deletes hidden timeline events for a user with specific row id '''
    try:
        result = db_conn.execute(text('''
            DELETE FROM hide_user_timeline_event WHERE
            user_id = :user_id AND
            event_type = :event_type AND
            event_id = :event_id
        '''), {
            'user_id': user,
            'event_type': event_type,
            'event_id': event_id
        })
        db_conn.commit()
        return result.rowcount == 1
    except Exception as e:
        raise DatabaseException(str(e))
