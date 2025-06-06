import time
import base64
from typing import Optional

import requests

from flask import current_app

from data.model.external_service import ExternalServiceType
from listenbrainz.db import funkwhale
from listenbrainz.model.funkwhale import FunkwhaleServer

from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError, ExternalServiceInvalidGrantError
from listenbrainz.webserver import db_conn

FUNKWHALE_API_RETRIES = 5

def _get_funkwhale_token(grant_type: str, token: str, host_url: str) -> requests.Response:
    """ Fetch access token or refresh token from funkwhale auth api

    Args:
        grant_type (str): should be "authorization_code" to retrieve access token and "refresh_token" to refresh tokens
        token (str): authorization code to retrieve access token first time and refresh token to refresh access tokens
        host_url (str): the Funkwhale server URL

    Returns:
        response from the funkwhale authentication endpoint
    """
    client_id = current_app.config['FUNKWHALE_CLIENT_ID']
    client_secret = current_app.config['FUNKWHALE_CLIENT_SECRET']
    auth_header = base64.b64encode((client_id + ':' + client_secret).encode('ascii'))
    headers = {'Authorization': 'Basic %s' % auth_header.decode('ascii')}

    token_key = "refresh_token" if grant_type == "refresh_token" else "code"
    payload = {
        'redirect_uri': current_app.config['FUNKWHALE_CALLBACK_URL'],
        token_key: token,
        'grant_type': grant_type,
    }

    token_url = f"{host_url}/api/v1/oauth/token"
    return requests.post(token_url, data=payload, headers=headers, verify=True)

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
        access_token = token['access_token']
        refresh_token = token['refresh_token']
        expires_at = int(time.time()) + token['expires_in']

        # Get user details from Funkwhale API
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f"{host_url}/users/me", headers=headers)
        if response.status_code != 200:
            raise ExternalServiceError("Could not get user details from Funkwhale")
        details = response.json()
        external_user_id = details["id"]

        # Create new FunkwhaleServer entry
        server = FunkwhaleServer(
            user_id=user_id,
            host_url=host_url,
            client_id=self.client_id,
            client_secret=self.client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=expires_at
        )
        db_conn.session.add(server)
        db_conn.session.commit()
        return True

    def get_authorize_url(self, host_url: str, permissions: list[str]):
        """ Returns the OAuth authorization URL for Funkwhale.
        Args:
            host_url: The Funkwhale server URL
            permissions: List of permissions needed
        """
        scope = ' '.join(permissions)
        return f"{host_url}/oauth/authorize?client_id={self.client_id}&response_type=code&redirect_uri={self.redirect_url}&scope={scope}"

    def fetch_access_token(self, host_url: str, code: str):
        """ Get a valid Funkwhale Access token given the code.
        Args:
            host_url: The Funkwhale server URL
            code: The authorization code
        Returns:
            a dict with the following keys
            {
                'access_token',
                'token_type',
                'scope',
                'expires_in',
                'refresh_token',
            }
        """
        r = _get_funkwhale_token("authorization_code", code, host_url)
        if r.status_code != 200:
            raise ExternalServiceError(r.reason)
        return r.json()

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
        retries = FUNKWHALE_API_RETRIES
        response = None
        while retries > 0:
            response = _get_funkwhale_token("refresh_token", refresh_token, host_url)

            if response.status_code == 200:
                break
            elif response.status_code == 400:
                error_body = response.json()
                if "error" in error_body and error_body["error"] == "invalid_grant":
                    raise ExternalServiceInvalidGrantError(error_body)

            response = None  # some other error occurred
            retries -= 1

        if response is None:
            raise ExternalServiceAPIError('Could not refresh API Token for Funkwhale user')

        response = response.json()
        access_token = response['access_token']
        if "refresh_token" in response:
            refresh_token = response['refresh_token']
        expires_at = int(time.time()) + response['expires_in']

        # Update the FunkwhaleServer entry
        server = FunkwhaleServer.query.filter_by(user_id=user_id, host_url=host_url).first()
        if server:
            server.access_token = access_token
            server.refresh_token = refresh_token
            server.token_expiry = expires_at
            db_conn.session.commit()

        return self.get_user(user_id, host_url)

    def revoke_user(self, user_id: int, host_url: str):
        """ Delete the user's connection to external service.

        Args:
            user_id (int): the ListenBrainz row ID of the user
            host_url (str): the Funkwhale server URL
        """
        server = FunkwhaleServer.query.filter_by(user_id=user_id, host_url=host_url).first()
        if server:
            db_conn.session.delete(server)
            db_conn.session.commit()

    def user_oauth_token_has_expired(self, user: dict) -> bool:
        """ Check if the user's OAuth token has expired.

        Args:
            user: a user as returned by get_user
        Returns:
            True if the token has expired, False otherwise
        """
        return int(time.time()) >= user['token_expiry'] 