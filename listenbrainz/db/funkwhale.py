from typing import Optional, Dict, Any

from listenbrainz.model.funkwhale import FunkwhaleServer
from listenbrainz.webserver import db_conn

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
        'user_id': server.user_id,
        'host_url': server.host_url,
        'client_id': server.client_id,
        'client_secret': server.client_secret,
        'access_token': server.access_token,
        'refresh_token': server.refresh_token,
        'token_expiry': server.token_expiry
    } 