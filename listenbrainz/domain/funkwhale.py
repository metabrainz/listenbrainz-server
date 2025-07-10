
import time
import base64
from typing import Optional, List
from urllib.parse import urlencode
from datetime import datetime, timedelta

import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from flask import current_app, session

from listenbrainz.db import funkwhale as db_funkwhale
from listenbrainz.webserver import db_conn
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError, ExternalServiceInvalidGrantError

import sqlalchemy

FUNKWHALE_API_RETRIES = 5

class FunkwhaleService:
    def __init__(self):
        self.redirect_url = current_app.config['FUNKWHALE_CALLBACK_URL']

    def _get_or_create_oauth_credentials(self, host_url: str, client_id: str = None, client_secret: str = None, scopes: str = None) -> tuple:
        # Try to get server by host_url
        server = db_funkwhale.get_server_by_host_url(host_url)
        if server and server.get('client_id') and server.get('client_secret'):
            return server['client_id'], server['client_secret'], server['id']
        # If not found or missing credentials, create
        if not (client_id and client_secret and scopes):
            raise ExternalServiceError("Missing client_id, client_secret, or scopes for new Funkwhale server registration.")
        server_id = db_funkwhale.get_or_create_server(host_url, client_id, client_secret, scopes)
        return client_id, client_secret, server_id

    def get_user(self, user_id: int, host_url: str = None, refresh: bool = False) -> Optional[dict]:
        # Get server by host_url
        if not host_url:
            return None
        server = db_funkwhale.get_server_by_host_url(host_url)
        if not server:
            return None
        token = db_funkwhale.get_token(user_id, server['id'])
        if not token:
            return None
        user = {
            'user_id': user_id,
            'host_url': host_url,
            'client_id': server['client_id'],
            'client_secret': server['client_secret'],
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'token_expiry': token['token_expiry'],
            'funkwhale_server_id': server['id']
        }
        if refresh and self.user_oauth_token_has_expired(user):
            try:
                current_app.logger.debug(f"Refreshing expired Funkwhale token for user {user_id}")
                user = self.refresh_access_token(user_id, host_url, user['refresh_token'])
            except ExternalServiceInvalidGrantError:
                current_app.logger.warning(f"Funkwhale token refresh failed - user {user_id} revoked access")
                # Don't return None - return the user with expired token so frontend can handle
                # The frontend will get an error when trying to use the expired token and can prompt for reconnection
                pass  # Keep the existing user object with expired token
            except Exception as e:
                current_app.logger.error(f"Funkwhale token refresh failed for user {user_id}: {e}")
                # Don't return None - return the user with expired token so frontend can handle
                # The frontend will get an error when trying to use the expired token and can prompt for reconnection
                pass  # Keep the existing user object with expired token
        return user

    def add_new_user(self, user_id: int, host_url: str, token: dict, client_id: str, client_secret: str, scopes: str) -> bool:
        access_token = token['access_token']
        refresh_token = token['refresh_token']
        expires_at = int(time.time()) + token['expires_in']
        from datetime import timezone
        token_expiry_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        # Register or get server
        client_id, client_secret, server_id = self._get_or_create_oauth_credentials(host_url, client_id, client_secret, scopes)
        # Save token
        db_funkwhale.save_token(user_id, server_id, access_token, refresh_token, token_expiry_datetime)
        return True

    def get_authorize_url(self, host_url: str, scopes: List[str], state: Optional[str] = None) -> str:
        # Ensure host_url doesn't end with a slash
        host_url = host_url.rstrip('/')
        # Check if server exists with valid credentials
        server = db_funkwhale.get_server_by_host_url(host_url)
        if server and server.get('client_id') and server.get('client_secret'):
            client_id = server['client_id']
            current_app.logger.debug(f"Using existing OAuth app for {host_url} with client_id {client_id[:8]}...")
        else:
            # Create OAuth app on Funkwhale only if none exists
            current_app.logger.debug(f"Creating new OAuth app for {host_url}")
            app_data = {
                'name': 'ListenBrainz',
                'website': host_url,
                'redirect_uris': self.redirect_url,
                'scopes': ' '.join(scopes)
            }
            response = requests.post(f"{host_url}/api/v1/oauth/apps/", json=app_data, timeout=30)
            if response.status_code != 201:
                raise ExternalServiceError(f"Failed to create OAuth app: {response.status_code} - {response.text}")
            app_credentials = response.json()
            client_id = app_credentials['client_id']
            client_secret = app_credentials['client_secret']
            current_app.logger.debug(f"Created new OAuth app with client_id {client_id[:8]}...")
            db_funkwhale.get_or_create_server(host_url, client_id, client_secret, ' '.join(scopes))
        auth_url = f"{host_url}/api/v1/oauth/authorize"
        oauth = OAuth2Session(
            client_id=client_id,
            redirect_uri=self.redirect_url,
            scope=scopes,
            state=state
        )
        authorization_url, _ = oauth.authorization_url(auth_url)
        return authorization_url

    def fetch_access_token(self, code: str):
        host_url = session.get('funkwhale_host_url')
        if not host_url:
            raise ExternalServiceError("No host URL found in session")
        server = db_funkwhale.get_server_by_host_url(host_url)
        if not server:
            raise ExternalServiceError("No Funkwhale server found for host_url")
        client_id = server['client_id']
        client_secret = server['client_secret']
        oauth = OAuth2Session(
            client_id=client_id,
            redirect_uri=self.redirect_url
        )
        token_url = f"{host_url}/api/v1/oauth/token/"
        try:
            return oauth.fetch_token(
                token_url,
                client_secret=client_secret,
                code=code,
                include_client_id=True
            )
        except requests.exceptions.RequestException as e:
            raise ExternalServiceError(f"Failed to fetch access token: {str(e)}")
        except InvalidGrantError as e:
            raise ExternalServiceInvalidGrantError("Invalid authorization code") from e

    def refresh_access_token(self, user_id: int, host_url: str, refresh_token: str):
        server = db_funkwhale.get_server_by_host_url(host_url)
        if not server:
            raise ExternalServiceError("No Funkwhale server found for host_url")
        client_id = server['client_id']
        client_secret = server['client_secret']
        
        # Log client_id for debugging (but not client_secret for security)
        current_app.logger.debug(f"Using client_id {client_id[:8]}... for user {user_id} at {host_url}")
        current_app.logger.debug(f"Server record ID: {server['id']}, scopes: {server.get('scopes', 'unknown')}")
        
        oauth = OAuth2Session(
            redirect_uri=self.redirect_url
        )
        token_url = f"{host_url}/api/v1/oauth/token/"
        try:
            current_app.logger.debug(f"Attempting to refresh Funkwhale token for user {user_id} at {host_url}")
            current_app.logger.debug(f"Token URL: {token_url}")
            current_app.logger.debug(f"Refresh token length: {len(refresh_token) if refresh_token else 0}")
            
            token = oauth.refresh_token(
                token_url,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                include_client_id=True
            )
        except InvalidGrantError as e:
            current_app.logger.warning(f"Funkwhale token refresh failed - invalid grant for user {user_id}: {e}")
            # Log more details for debugging
            current_app.logger.warning(f"Failed refresh details: client_id={client_id[:8]}..., host_url={host_url}")
            raise ExternalServiceInvalidGrantError("User revoked access") from e
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Funkwhale token refresh network error for user {user_id}: {e}")
            raise ExternalServiceAPIError(f"Could not connect to Funkwhale server: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error during Funkwhale token refresh for user {user_id}: {e}")
            # Log more details for debugging client issues
            current_app.logger.error(f"Error details: client_id={client_id[:8]}..., host_url={host_url}, error_type={type(e).__name__}")
            
            # If it's an invalid_client error, the OAuth app might have been deleted on Funkwhale
            # Log the issue but DON'T delete the token - let the frontend handle reconnection
            if "invalid_client" in str(e).lower():
                current_app.logger.warning(f"Invalid client error suggests OAuth app was deleted on Funkwhale server {host_url}")
                current_app.logger.warning(f"User {user_id} will need to manually reconnect to fix this issue")
                # Keep the token so user remains "connected" - frontend can show reconnection prompt
            
            raise ExternalServiceError(f"Token refresh failed: {str(e)}")
        
        access_token = token['access_token']
        new_refresh_token = token.get('refresh_token', refresh_token)
        expires_at = int(time.time()) + token['expires_in']
        from datetime import timezone
        token_expiry_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        
        current_app.logger.debug(f"Successfully refreshed Funkwhale token for user {user_id}, expires at {token_expiry_datetime}")
        db_funkwhale.update_token(user_id, server['id'], access_token, new_refresh_token, token_expiry_datetime)
        return self.get_user(user_id, host_url)

    def revoke_user(self, user_id: int, host_url: str):
        server = db_funkwhale.get_server_by_host_url(host_url)
        if not server:
            return
        db_funkwhale.delete_token(user_id, server['id'])

    def remove_user(self, user_id: int):
        # Remove all tokens for this user across all servers
        db_conn.execute(sqlalchemy.text("""
            DELETE FROM funkwhale_tokens WHERE user_id = :user_id
        """), {'user_id': user_id})
        db_conn.commit()

    def user_oauth_token_has_expired(self, user: dict) -> bool:
        from datetime import timezone
        token_expiry = user['token_expiry']
        current_app.logger.debug(f"Checking token expiry for user {user.get('user_id')}: {token_expiry}")
        
        if isinstance(token_expiry, datetime):
            now = datetime.now(timezone.utc)
            if token_expiry.tzinfo is None:
                # Assume stored timestamps are in UTC if no timezone info
                token_expiry = token_expiry.replace(tzinfo=timezone.utc)
            # Add a small buffer (30 seconds) to avoid edge cases
            is_expired = now >= (token_expiry - timedelta(seconds=30))
            current_app.logger.debug(f"Token expiry check: now={now}, expiry={token_expiry}, expired={is_expired}")
            return is_expired
        else:
            # Handle integer timestamps
            now_ts = int(time.time())
            is_expired = now_ts >= (token_expiry - 30)
            current_app.logger.debug(f"Token expiry check (timestamp): now={now_ts}, expiry={token_expiry}, expired={is_expired}")
            return is_expired