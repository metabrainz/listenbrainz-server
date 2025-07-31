import sqlalchemy
from listenbrainz.webserver import db_conn
from typing import Optional, Dict, Any


def get_or_create_server(host_url: str) -> int:
    """Get or create a Navidrome server entry"""
    # First, try to get existing server
    existing_server = get_server_by_host_url(host_url)
    if existing_server:
        return existing_server['id']
    
    # If no server exists, create it
    result = db_conn.execute(sqlalchemy.text("""
        INSERT INTO navidrome_servers (host_url)
        VALUES (:host_url)
        ON CONFLICT (host_url) DO UPDATE SET
            host_url = EXCLUDED.host_url
        RETURNING id
    """), {
        'host_url': host_url
    })
    db_conn.commit()
    return result.fetchone().id


def get_server_by_host_url(host_url: str) -> Optional[Dict[str, Any]]:
    """Get server by host URL"""
    result = db_conn.execute(sqlalchemy.text("""
        SELECT * FROM navidrome_servers WHERE host_url = :host_url
    """), {'host_url': host_url})
    row = result.mappings().first()
    return dict(row) if row else None


def save_user_token(user_id: int, host_url: str, username: str, access_token: str) -> int:
    """Save user token for Navidrome (one connection per user)"""
    # Get or create server
    server_id = get_or_create_server(host_url)
    
    # Save/update user token 
    result = db_conn.execute(sqlalchemy.text("""
        INSERT INTO navidrome_tokens (user_id, navidrome_server_id, username, access_token)
        VALUES (:user_id, :navidrome_server_id, :username, :access_token)
        ON CONFLICT (user_id, navidrome_server_id) DO UPDATE SET
            username = EXCLUDED.username,
            access_token = EXCLUDED.access_token
        RETURNING id
    """), {
        'user_id': user_id,
        'navidrome_server_id': server_id,
        'username': username,
        'access_token': access_token
    })
    db_conn.commit()
    return result.fetchone().id


def get_user_token(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's Navidrome connection (only one per user)"""
    result = db_conn.execute(sqlalchemy.text("""
        SELECT t.*, s.host_url
        FROM navidrome_tokens t
        JOIN navidrome_servers s ON t.navidrome_server_id = s.id
        WHERE t.user_id = :user_id
        LIMIT 1
    """), {'user_id': user_id})
    row = result.mappings().first()
    return dict(row) if row else None


def delete_user_token(user_id: int) -> None:
    """Delete user's Navidrome connection"""
    db_conn.execute(sqlalchemy.text("""
        DELETE FROM navidrome_tokens WHERE user_id = :user_id
    """), {'user_id': user_id})
    db_conn.commit()
