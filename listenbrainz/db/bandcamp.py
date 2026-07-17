from typing import Any, Dict, Optional

import sqlalchemy


def save_user_token(
    db_conn,
    user_id: int,
    host_url: str,
    username: str,
    encrypted_password: str,
) -> int:
    """Save encrypted Bandcamp Subsonic credentials for a user."""
    result = db_conn.execute(sqlalchemy.text("""
        INSERT INTO bandcamp_tokens AS bt (user_id, username, encrypted_password)
        VALUES (:user_id, :username, :encrypted_password)
        ON CONFLICT (user_id) DO UPDATE SET
            username = EXCLUDED.username,
            encrypted_password = EXCLUDED.encrypted_password,
            last_updated = NOW()
        RETURNING id
    """), {
        "user_id": user_id,
        "username": username,
        "encrypted_password": encrypted_password,
    })
    db_conn.commit()
    return result.fetchone().id


def get_user_token(db_conn, user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's Bandcamp connection."""
    result = db_conn.execute(sqlalchemy.text("""
        SELECT *
          FROM bandcamp_tokens
         WHERE user_id = :user_id
         LIMIT 1
    """), {"user_id": user_id})
    row = result.mappings().first()
    return dict(row) if row else None


def delete_user_token(db_conn, user_id: int) -> None:
    """Delete user's Bandcamp connection."""
    db_conn.execute(sqlalchemy.text("""
        DELETE FROM bandcamp_tokens WHERE user_id = :user_id
    """), {"user_id": user_id})
    db_conn.commit()
