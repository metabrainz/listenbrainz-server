from typing import List

import sqlalchemy

VALID_RELATIONSHIP_TYPES = ("follow",)


def insert(db_conn, user_id: int, artist_mbid: str, relationship_type: str) -> None:
    """
    Insert a user artist relationship like follow.
    Uses ON CONFLICT DO NOTHING for idempotent inserts.
    """

    if relationship_type not in VALID_RELATIONSHIP_TYPES:
        raise ValueError(f"Invalid relationship type: {relationship_type}")

    db_conn.execute(
        sqlalchemy.text("""
        INSERT INTO user_artist_relationship (user_id, artist_mbid, relationship_type)
             VALUES (:user_id, :artist_mbid, :relationship_type)
        ON CONFLICT (user_id, artist_mbid, relationship_type)
         DO NOTHING
    """),
        {
            "user_id": user_id,
            "artist_mbid": artist_mbid,
            "relationship_type": relationship_type,
        },
    )
    db_conn.commit()


def delete(db_conn, user_id: int, artist_mbid: str, relationship_type: str) -> None:
    """
    Delete a user artist relationship.
    """

    if relationship_type not in VALID_RELATIONSHIP_TYPES:
        raise ValueError(f"Invalid relationship type: {relationship_type}")

    db_conn.execute(
        sqlalchemy.text("""
        DELETE
        FROM user_artist_relationship
        WHERE user_id = :user_id
          AND artist_mbid = :artist_mbid
          AND relationship_type = :relationship_type
    """),
        {
            "user_id": user_id,
            "artist_mbid": artist_mbid,
            "relationship_type": relationship_type,
        },
    )
    db_conn.commit()


def is_following_artist(db_conn, user_id: int, artist_mbid: str) -> bool:
    """
    Check whether the user is following the specified artist.
    """

    result = db_conn.execute(
        sqlalchemy.text("""
        SELECT COUNT(*) AS cnt
        FROM user_artist_relationship
        WHERE user_id = :user_id
          AND artist_mbid = :artist_mbid
          AND relationship_type = 'follow'
    """),
        {
            "user_id": user_id,
            "artist_mbid": artist_mbid,
        },
    )
    return result.fetchone().cnt > 0


def get_followed_artist_mbids(
    db_conn, user_id: int, limit: int = 50, offset: int = 0
) -> List[dict]:
    """
    Returns a paginated list of dicts containing the artist_mbid for artists
    the user follows, ordered by most recently followed first.
    """

    result = db_conn.execute(
        sqlalchemy.text("""
        SELECT artist_mbid::TEXT
        FROM user_artist_relationship
        WHERE user_id = :user_id
          AND relationship_type = 'follow'
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


def get_users_following_artist(db_conn, artist_mbid: str) -> List[dict]:
    """
    Returns a list of user IDs who follow the specified artist.
    """

    result = db_conn.execute(
        sqlalchemy.text("""
        SELECT user_id
        FROM user_artist_relationship
        WHERE artist_mbid = :artist_mbid
          AND relationship_type = 'follow'
    """),
        {
            "artist_mbid": artist_mbid,
        },
    )
    return result.mappings().all()
