
import time
from typing import Optional, List
from datetime import datetime, timedelta, timezone

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

    def get_user(self, user_id: int, host_url: str = None, refresh: bool = False) -> Optional[dict]:
        if not host_url:
            return None
        server = db_funkwhale.get_server_by_host_url(db_conn, host_url)
        if not server:
            return None
        token = db_funkwhale.get_token(db_conn, user_id, server["id"])
        if not token:
            return None
        user = {
            "user_id": user_id,
            "host_url": host_url,
            "client_id": server["client_id"],
            "client_secret": server["client_secret"],
            "access_token": token["access_token"],
            "refresh_token": token["refresh_token"],
            "token_expiry": token["token_expiry"],
            "funkwhale_server_id": server["id"]
        }
        if refresh and self.user_oauth_token_has_expired(user):
            try:
                user = self.refresh_access_token(user_id, server, user["refresh_token"])
            except:
                return None
        return user

    def add_new_user(self, user_id: int, server_id: int, token: dict) -> bool:
        access_token = token['access_token']
        refresh_token = token['refresh_token']
        expires_at = int(time.time()) + token['expires_in']
        token_expiry_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        db_funkwhale.save_token(db_conn, user_id, server_id, access_token, refresh_token, token_expiry_datetime)
        return True

    def get_authorize_url(self, host_url: str, scopes: List[str], state: Optional[str] = None) -> str:
        host_url = host_url.rstrip('/')
        server = db_funkwhale.get_server_by_host_url(db_conn, host_url)

        if server:
            client_id = server['client_id']
            current_app.logger.debug(f"Using existing OAuth app for {host_url} with client_id {client_id[:8]}...")
        else:
            current_app.logger.debug(f"Creating new OAuth app for {host_url}")
            app_data = {
                'name': 'ListenBrainz',
                'website': host_url,
                'redirect_uris': self.redirect_url,
                'scopes': ' '.join(scopes)
            }
            response = requests.post(f"{host_url}/api/v1/oauth/apps/", json=app_data, timeout=30)
            if response.status_code not in {200, 201}:
                raise ExternalServiceError(f"Failed to create OAuth app: {response.status_code} - {response.text}")
            app_credentials = response.json()
            client_id = app_credentials['client_id']
            client_secret = app_credentials['client_secret']
            current_app.logger.debug(f"Created new OAuth app with client_id {client_id[:8]}...")
            db_funkwhale.get_or_create_server(db_conn, host_url, client_id, client_secret, ' '.join(scopes))

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
        server = db_funkwhale.get_server_by_host_url(db_conn, host_url)
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

    def refresh_access_token(self, user_id: int, server: dict, refresh_token: str):
        oauth = OAuth2Session(
            redirect_uri=self.redirect_url
        )
        token_url = f"{server['host_url']}/api/v1/oauth/token/"
        try:
            token = oauth.refresh_token(
                token_url,
                client_id=server['client_id'],
                client_secret=server['client_secret'],
                refresh_token=refresh_token,
                include_client_id=True
            )
        except InvalidGrantError as e:
            current_app.logger.warning(f"Funkwhale token refresh failed - invalid grant for user {user_id}: {e}")
            raise ExternalServiceInvalidGrantError("User revoked access") from e
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Funkwhale token refresh network error for user {user_id}: {e}")
            raise ExternalServiceAPIError(f"Could not connect to Funkwhale server: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error during Funkwhale token refresh for user {user_id}: {e}")
            # If it's an invalid_client error, the OAuth app might have been deleted on Funkwhale
            # Log the issue but DON'T delete the token - let the frontend handle reconnection
            if "invalid_client" in str(e).lower():
                current_app.logger.warning(f"Invalid client error suggests OAuth app was deleted on Funkwhale server {server['host_url']}")
                current_app.logger.warning(f"User {user_id} will need to manually reconnect to fix this issue")
                # Keep the token so user remains "connected" - frontend can show reconnection prompt
            
            raise ExternalServiceError(f"Token refresh failed: {str(e)}")
        
        access_token = token['access_token']
        new_refresh_token = token.get('refresh_token', refresh_token)
        expires_at = int(time.time()) + token['expires_in']
        token_expiry_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        
        current_app.logger.debug(f"Successfully refreshed Funkwhale token for user {user_id}, expires at {token_expiry_datetime}")
        db_funkwhale.update_token(db_conn, user_id, server['id'], access_token, new_refresh_token, token_expiry_datetime)
        return self.get_user(user_id, server['host_url'])

    def revoke_user(self, user_id: int, host_url: str):
        server = db_funkwhale.get_server_by_host_url(db_conn, host_url)
        if not server:
            return
        db_funkwhale.delete_token(db_conn, user_id, server['id'])

    def remove_user(self, user_id: int):
        # Remove all tokens for this user across all servers
        db_conn.execute(sqlalchemy.text("""
            DELETE FROM funkwhale_tokens WHERE user_id = :user_id
        """), {'user_id': user_id})
        db_conn.commit()

    def user_oauth_token_has_expired(self, user: dict) -> bool:
        token_expiry = user["token_expiry"]
        now = datetime.now(timezone.utc)
        is_expired = now >= (token_expiry - timedelta(seconds=30))
        return is_expired