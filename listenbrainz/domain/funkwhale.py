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
        self.client_id = current_app.config['FUNKWHALE_CLIENT_ID']
        self.client_secret = current_app.config['FUNKWHALE_CLIENT_SECRET']
        self.redirect_url = current_app.config['FUNKWHALE_CALLBACK_URL']

    def get_user(self, user_id: int, host_url: str, refresh: bool = False) -> Optional[dict]:
        """ If refresh = True, then check whether the access token has expired and refresh it
        before returning the user."""
        user = funkwhale.get_user(db_conn, user_id, host_url)
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

            # Check if a server entry already exists for this user and host
            server = FunkwhaleServer.query.filter_by(user_id=user_id, host_url=host_url).first()

            if server:
                # Update existing entry
                server.access_token = access_token
                server.refresh_token = refresh_token
                server.token_expiry = token_expiry_datetime
                current_app.logger.info("Updated existing Funkwhale connection for user %s at %s", user_id, host_url)
            else:
                # Create new FunkwhaleServer entry
                server = FunkwhaleServer(
                    user_id=user_id,
                    host_url=host_url,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
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
        auth_url = f"{host_url}/api/v1/oauth/authorize"
        
        oauth = OAuth2Session(
            client_id=self.client_id,
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
                
            oauth = OAuth2Session(
                client_id=self.client_id,
                redirect_uri=self.redirect_url
            )
            token_url = f"{host_url}/api/v1/oauth/token/"
            return oauth.fetch_token(
                token_url,
                client_secret=self.client_secret,
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
            oauth = OAuth2Session(
                client_id=self.client_id,
                redirect_uri=self.redirect_url
            )
            token_url = f"{host_url}/api/v1/oauth/token/"
            token = oauth.refresh_token(
                token_url,
                client_secret=self.client_secret,
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

    def user_oauth_token_has_expired(self, user: dict) -> bool:
        """ Check if the user's OAuth token has expired.

        Args:
            user: a user as returned by get_user
        Returns:
            True if the token has expired, False otherwise
        """
        return int(time.time()) >= user['token_expiry'] 