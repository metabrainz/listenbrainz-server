from typing import List

import sqlalchemy


def watch_event(db_conn, user_id: int, event_mbid: str) -> None:
    """
    Mark an event as watched by the user.
    Uses ON CONFLICT DO NOTHING for idempotent inserts.
    """
    db_conn.execute(
        sqlalchemy.text("""
        INSERT INTO event_interaction (user_id, event_mbid, interaction_type)
        VALUES (:user_id, :event_mbid, 'watch')
        ON CONFLICT (user_id, event_mbid, interaction_type) DO NOTHING
    """),
        {
            "user_id": user_id,
            "event_mbid": event_mbid,
        },
    )
    db_conn.commit()


def unwatch_event(db_conn, user_id: int, event_mbid: str) -> None:
    """
    Remove a watch interaction for the user on the given event.
    """
    db_conn.execute(
        sqlalchemy.text("""
        DELETE
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
    db_conn.commit()


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
