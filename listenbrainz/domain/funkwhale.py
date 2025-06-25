import time
import base64
from typing import Optional, List
from urllib.parse import urlencode
from datetime import datetime

import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from flask import current_app, session

from data.model.external_service import ExternalServiceType
from listenbrainz.db import funkwhale
from listenbrainz.model.funkwhale import FunkwhaleServer
from listenbrainz.model import db

from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError, ExternalServiceInvalidGrantError
from listenbrainz.webserver import db_conn

FUNKWHALE_API_RETRIES = 5

class FunkwhaleService:
    def __init__(self):
        self.redirect_url = current_app.config.get('FUNKWHALE_CALLBACK_URL', 
                                                   current_app.config['SERVER_ROOT_URL'] + '/settings/music-services/funkwhale/callback/')

    def _create_oauth_app(self, host_url: str) -> dict:
        """Create an OAuth application on the Funkwhale server.
        
        Args:
            host_url: The Funkwhale server URL
            
        Returns:
            dict: OAuth app credentials with client_id and client_secret
            
        Raises:
            ExternalServiceError: If app creation fails
        """
        app_data = {
            'name': 'ListenBrainz',
            'website': host_url,
            'redirect_uris': self.redirect_url,
            'scopes': 'read:profile read:libraries read:favorites read:listenings read:follows read:playlists read:radios'
        }
        
        try:
            response = requests.post(f"{host_url}/api/v1/oauth/apps/", json=app_data, timeout=30)
            if response.status_code == 201:
                return response.json()
            else:
                raise ExternalServiceError(f"Failed to create OAuth app: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            raise ExternalServiceError(f"Network error creating OAuth app: {str(e)}")

    def _get_or_create_oauth_credentials(self, host_url: str) -> tuple[str, str]:
        """Get existing OAuth credentials for a server or create new ones.
        
        Args:
            host_url: The Funkwhale server URL
            
        Returns:
            tuple: (client_id, client_secret)
        """
        # Check if we already have credentials for any user on this server
        server = FunkwhaleServer.query.filter_by(host_url=host_url).filter(
            FunkwhaleServer.client_id.isnot(None),
            FunkwhaleServer.client_secret.isnot(None)
        ).first()
        
        if server:
            return server.client_id, server.client_secret
        
        # Create new OAuth application
        app_credentials = self._create_oauth_app(host_url)
        client_id = app_credentials['client_id']
        client_secret = app_credentials['client_secret']
        
        current_app.logger.info(f"Created OAuth app for Funkwhale server: {host_url}")
        return client_id, client_secret

    def get_user(self, user_id: int, host_url: str = None, refresh: bool = False) -> Optional[dict]:
        """ If refresh = True, then check whether the access token has expired and refresh it
        before returning the user. If host_url is not provided, returns the first connection for the user."""
        if host_url:
            user = funkwhale.get_user(db_conn, user_id, host_url)
        else:
            # For compatibility with generic service interface, get the first connection
            server = FunkwhaleServer.query.filter_by(user_id=user_id).first()
            if not server:
                return None
            # Use the db function to avoid duplication
            user = funkwhale.get_user(db_conn, user_id, server.host_url)
        
        if user and refresh and self.user_oauth_token_has_expired(user):
            user = self.refresh_access_token(user['user_id'], user['host_url'], user['refresh_token'])
        return user

    def add_new_user(self, user_id: int, host_url: str, token: dict) -> bool:
        """Create a funkwhale row for a user based on OAuth access tokens

        Args:
            user_id: A flask auth `current_user.id`
            host_url: The Funkwhale server URL
            token: A funkwhale access token
        """
        try:
            access_token = token['access_token']
            refresh_token = token['refresh_token']
            expires_at = int(time.time()) + token['expires_in']

            # Convert epoch time to datetime object for PostgreSQL timestamp with time zone
            token_expiry_datetime = datetime.fromtimestamp(expires_at)

            # Get user details from Funkwhale API
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(f"{host_url}/api/v1/users/me", headers=headers)
            if response.status_code != 200:
                raise ExternalServiceError(f"Could not get user details from Funkwhale: {response.text}")
            details = response.json()
            external_user_id = details["id"]

            # Get OAuth credentials for this server
            client_id, client_secret = self._get_or_create_oauth_credentials(host_url)

            # Check if a server entry already exists for this user and host
            server = FunkwhaleServer.query.filter_by(user_id=user_id, host_url=host_url).first()

            if server:
                # Update existing entry
                server.client_id = client_id
                server.client_secret = client_secret
                server.access_token = access_token
                server.refresh_token = refresh_token
                server.token_expiry = token_expiry_datetime
                current_app.logger.info("Updated existing Funkwhale connection for user %s at %s", user_id, host_url)
            else:
                # Create new FunkwhaleServer entry
                server = FunkwhaleServer(
                    user_id=user_id,
                    host_url=host_url,
                    client_id=client_id,
                    client_secret=client_secret,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expiry=token_expiry_datetime
                )
                db.session.add(server)
                current_app.logger.info("Created new Funkwhale connection for user %s at %s", user_id, host_url)
            
            db.session.commit()
            return True
        except KeyError as e:
            raise ExternalServiceError(f"Invalid token response: missing {str(e)}")
        except Exception as e:
            current_app.logger.error("Failed to add/update Funkwhale user connection: %s", str(e), exc_info=True)
            raise ExternalServiceError(f"Failed to add/update user: {str(e)}")

    def get_authorize_url(self, host_url: str, scopes: List[str], state: Optional[str] = None) -> str:
        """Get the authorization URL for Funkwhale OAuth.
        
        Args:
            host_url: The Funkwhale server URL
            scopes: List of scopes to request
            state: Optional state parameter for security
            
        Returns:
            The authorization URL
        """
        # Ensure host_url doesn't end with a slash
        host_url = host_url.rstrip('/')
        
        # Get or create OAuth credentials for this server
        client_id, _ = self._get_or_create_oauth_credentials(host_url)
        
        auth_url = f"{host_url}/api/v1/oauth/authorize"
        
        oauth = OAuth2Session(
            client_id=client_id,
            redirect_uri=self.redirect_url,
            scope=[
                'read:profile',
                'read:libraries',
                'read:favorites',
                'read:listenings',
                'read:follows',
                'read:playlists',
                'read:radios'
            ],
            state=state
        )
        authorization_url, _ = oauth.authorization_url(auth_url)
        return authorization_url

    def fetch_access_token(self, code: str):
        """Fetch access token from Funkwhale using the authorization code.
        
        Args:
            code: The authorization code from Funkwhale
            
        Returns:
            The token data dictionary
        """
        try:
            host_url = session.get('funkwhale_host_url')
            if not host_url:
                raise ExternalServiceError("No host URL found in session")
            
            # Get OAuth credentials for this server
            client_id, client_secret = self._get_or_create_oauth_credentials(host_url)
                
            oauth = OAuth2Session(
                client_id=client_id,
                redirect_uri=self.redirect_url
            )
            token_url = f"{host_url}/api/v1/oauth/token/"
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
        """ Refreshes the user token for the given funkwhale user.
        Args:
            user_id (int): the ListenBrainz row ID of the user whose token is to be refreshed
            host_url (str): the Funkwhale server URL
            refresh_token (str): the refresh token to use for refreshing access token
        Returns:
            user (dict): the same user with updated tokens
        Raises:
            FunkwhaleAPIError: if unable to refresh funkwhale user token
            FunkwhaleInvalidGrantError: if the user has revoked authorization to funkwhale
        """
        try:
            # Get OAuth credentials for this server
            server = FunkwhaleServer.query.filter_by(user_id=user_id, host_url=host_url).first()
            if not server or not server.client_id or not server.client_secret:
                # Fallback: try to get/create credentials
                client_id, client_secret = self._get_or_create_oauth_credentials(host_url)
            else:
                client_id, client_secret = server.client_id, server.client_secret
            
            oauth = OAuth2Session(
                client_id=client_id,
                redirect_uri=self.redirect_url
            )
            token_url = f"{host_url}/api/v1/oauth/token/"
            token = oauth.refresh_token(
                token_url,
                client_secret=client_secret,
                refresh_token=refresh_token,
                include_client_id=True
            )
        except InvalidGrantError as e:
            raise ExternalServiceInvalidGrantError("User revoked access") from e
        except requests.exceptions.RequestException as e:
            raise ExternalServiceAPIError(f"Could not connect to Funkwhale server: {str(e)}")

        try:
            access_token = token['access_token']
            if "refresh_token" in token:
                refresh_token = token['refresh_token']
            expires_at = int(time.time()) + token['expires_in']

            # Convert epoch time to datetime object for PostgreSQL timestamp with time zone
            token_expiry_datetime = datetime.fromtimestamp(expires_at)

            # Update the FunkwhaleServer entry
            server = FunkwhaleServer.query.filter_by(user_id=user_id, host_url=host_url).first()
            if server:
                server.access_token = access_token
                server.refresh_token = refresh_token
                server.token_expiry = token_expiry_datetime
                db.session.commit()

            return self.get_user(user_id, host_url)
        except (KeyError, ValueError) as e:
            raise ExternalServiceError(f"Invalid token response: {str(e)}")

    def revoke_user(self, user_id: int, host_url: str):
        """ Delete the user's connection to external service.

        Args:
            user_id (int): the ListenBrainz row ID of the user
            host_url (str): the Funkwhale server URL
        """
        server = FunkwhaleServer.query.filter_by(user_id=user_id, host_url=host_url).first()
        if server:
            db.session.delete(server)
            db.session.commit()

    def remove_user(self, user_id: int):
        """ Delete all Funkwhale server connections for a user. This method is called
        when a user disables Funkwhale integration completely.

        Args:
            user_id (int): the ListenBrainz row ID of the user
        """
        servers = FunkwhaleServer.query.filter_by(user_id=user_id).all()
        for server in servers:
            db.session.delete(server)
        if servers:
            db.session.commit()
            current_app.logger.info(f"Removed {len(servers)} Funkwhale server connections for user {user_id}")

    def user_oauth_token_has_expired(self, user: dict) -> bool:
        """ Check if the user's OAuth token has expired.

        Args:
            user: a user as returned by get_user
        Returns:
            True if the token has expired, False otherwise
        """
        from datetime import timezone
        
        token_expiry = user['token_expiry']
        if isinstance(token_expiry, datetime):
            # Compare datetime objects using UTC timezone
            now = datetime.now(timezone.utc)
            if token_expiry.tzinfo is None:
                token_expiry = token_expiry.replace(tzinfo=timezone.utc)
            return now >= token_expiry
        else:
            # Fallback: assume it's a timestamp integer
            return int(time.time()) >= token_expiry