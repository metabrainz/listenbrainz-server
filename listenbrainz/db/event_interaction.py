from typing import List

import sqlalchemy


def watch_event(db_conn, user_id: int, event_mbid: str) -> bool:
    """
    Mark an event as watched by the user.
    Uses ON CONFLICT DO NOTHING for idempotent inserts.

    Returns True if a new watch was created, False if the user was already
    watching the event.
    """
    result = db_conn.execute(
        sqlalchemy.text("""
        INSERT INTO event_interaction (user_id, event_mbid, interaction_type)
        VALUES (:user_id, :event_mbid, 'watch')
        ON CONFLICT (user_id, event_mbid, interaction_type) DO NOTHING
        RETURNING 1
    """),
        {
            "user_id": user_id,
            "event_mbid": event_mbid,
        },
    )
    row = result.fetchone()
    db_conn.commit()
    return row is not None


def unwatch_event(db_conn, user_id: int, event_mbid: str) -> bool:
    """
    Remove a watch interaction for the user on the given event.

    Returns True if a watch was removed, False if the user was not watching
    the event.
    """
    result = db_conn.execute(
        sqlalchemy.text("""
        DELETE
        FROM event_interaction
        WHERE user_id = :user_id
          AND event_mbid = :event_mbid
          AND interaction_type = 'watch'
        RETURNING 1
    """),
        {
            "user_id": user_id,
            "event_mbid": event_mbid,
        },
    )
    row = result.fetchone()
    db_conn.commit()
    return row is not None


def is_watching_event(db_conn, user_id: int, event_mbid: str) -> bool:
    """
    Check whether given user is watching the specified event
    """

    result = db_conn.execute(
        sqlalchemy.text("""
        SELECT COUNT(*) AS cnt
        FROM event_interaction
        WHERE user_id = :user_id
          AND event_mbid = :event_mbid
          AND interaction_type = 'watch'
    """),
        {
            "user_id": user_id,
            "event_mbid": event_mbid,
        },
    )
    return result.fetchone().cnt > 0


def get_watched_events(
    db_conn, user_id: int, limit: int = 50, offset: int = 0
) -> List[dict]:
    """
    Returns a paginated list of event MBIDs that the user is watching,
    ordered by most recently watched first.
    """

    result = db_conn.execute(
        sqlalchemy.text("""
        SELECT event_mbid::TEXT
        FROM event_interaction
        WHERE user_id = :user_id
          AND interaction_type = 'watch'
        ORDER BY created DESC
        LIMIT :limit OFFSET :offset
    """),
        {
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
        },
    )
    return result.mappings().all()


def get_watchers_count(db_conn, event_mbid: str) -> int:
    """Returns the number of users watching the specified event."""
    result = db_conn.execute(
        sqlalchemy.text("""
        SELECT COUNT(*) AS cnt
        FROM event_interaction
        WHERE event_mbid = :event_mbid
          AND interaction_type = 'watch'
    """),
        {
            "event_mbid": event_mbid,
        },
    )
    return result.fetchone().cnt


def get_users_watching_event(db_conn, event_mbid: str) -> List[dict]:
    """Returns a list of user IDs who are watching the specified event."""
    result = db_conn.execute(
        sqlalchemy.text("""
        SELECT user_id
        FROM event_interaction
        WHERE event_mbid = :event_mbid
          AND interaction_type = 'watch'
    """),
        {
            "event_mbid": event_mbid,
        },
    )
    return result.mappings().all()
