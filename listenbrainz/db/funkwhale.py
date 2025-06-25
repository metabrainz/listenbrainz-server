import sqlalchemy
from listenbrainz.webserver import db_conn
from typing import Optional, Dict, Any

def get_or_create_server(host_url: str, client_id: str, client_secret: str, scopes: str) -> int:
    result = db_conn.execute(sqlalchemy.text("""
        INSERT INTO funkwhale_servers (host_url, client_id, client_secret, scopes)
        VALUES (:host_url, :client_id, :client_secret, :scopes)
        ON CONFLICT (host_url) DO UPDATE SET
            client_id = EXCLUDED.client_id,
            client_secret = EXCLUDED.client_secret,
            scopes = EXCLUDED.scopes
        RETURNING id
    """), {
        'host_url': host_url,
        'client_id': client_id,
        'client_secret': client_secret,
        'scopes': scopes
    })
    db_conn.commit()
    return result.fetchone().id

def get_server_by_host_url(host_url: str) -> Optional[Dict[str, Any]]:
    result = db_conn.execute(sqlalchemy.text("""
        SELECT * FROM funkwhale_servers WHERE host_url = :host_url
    """), {'host_url': host_url})
    row = result.mappings().first()
    return dict(row) if row else None

def get_token(user_id: int, funkwhale_server_id: int) -> Optional[Dict[str, Any]]:
    result = db_conn.execute(sqlalchemy.text("""
        SELECT * FROM funkwhale_tokens WHERE user_id = :user_id AND funkwhale_server_id = :funkwhale_server_id
    """), {'user_id': user_id, 'funkwhale_server_id': funkwhale_server_id})
    row = result.mappings().first()
    return dict(row) if row else None

def save_token(user_id: int, funkwhale_server_id: int, access_token: str, refresh_token: str, token_expiry) -> int:
    result = db_conn.execute(sqlalchemy.text("""
        INSERT INTO funkwhale_tokens (user_id, funkwhale_server_id, access_token, refresh_token, token_expiry)
        VALUES (:user_id, :funkwhale_server_id, :access_token, :refresh_token, :token_expiry)
        ON CONFLICT (user_id, funkwhale_server_id) DO UPDATE SET
            access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            token_expiry = EXCLUDED.token_expiry
        RETURNING id
    """), {
        'user_id': user_id,
        'funkwhale_server_id': funkwhale_server_id,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_expiry': token_expiry
    })
    db_conn.commit()
    return result.fetchone().id

def update_token(user_id: int, funkwhale_server_id: int, access_token: str, refresh_token: str, token_expiry) -> None:
    db_conn.execute(sqlalchemy.text("""
        UPDATE funkwhale_tokens SET
            access_token = :access_token,
            refresh_token = :refresh_token,
            token_expiry = :token_expiry
        WHERE user_id = :user_id AND funkwhale_server_id = :funkwhale_server_id
    """), {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_expiry': token_expiry,
        'user_id': user_id,
        'funkwhale_server_id': funkwhale_server_id
    })
    db_conn.commit()

def delete_token(user_id: int, funkwhale_server_id: int) -> None:
    db_conn.execute(sqlalchemy.text("""
        DELETE FROM funkwhale_tokens WHERE user_id = :user_id AND funkwhale_server_id = :funkwhale_server_id
    """), {'user_id': user_id, 'funkwhale_server_id': funkwhale_server_id})
    db_conn.commit()

def get_user(connection, user_id: int, host_url: str) -> Optional[Dict[str, Any]]:
    """Get user's Funkwhale token and connection details
    
    Args:
        connection: Database connection
        user_id: ListenBrainz user ID
        host_url: Funkwhale server URL
        
    Returns:
        Dictionary containing user's Funkwhale connection details or None if not found
    """
    server = FunkwhaleServer.query.filter_by(user_id=user_id, host_url=host_url).first()
    if not server:
        return None
        
    return {
        'user_id': user_id,
        'host_url': server.host_url,
        'client_id': server.client_id,
        'client_secret': server.client_secret,
        'access_token': server.access_token,
        'refresh_token': server.refresh_token,
        'token_expiry': server.token_expiry
    } 