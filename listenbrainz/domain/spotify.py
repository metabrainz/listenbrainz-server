import time
import base64
from typing import Sequence, Optional

import requests
import spotipy

from flask import current_app
from spotipy import SpotifyOAuth

from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth
from listenbrainz.db import spotify

from listenbrainz.domain.external_service import ExternalServiceError, \
    ExternalServiceAPIError, ExternalServiceInvalidGrantError
from listenbrainz.domain.importer_service import ImporterService
from listenbrainz.webserver import db_conn

OAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'

SPOTIFY_IMPORT_PERMISSIONS = {
    'user-read-currently-playing',
    'user-read-recently-played',
}

SPOTIFY_LISTEN_PERMISSIONS = {
    'streaming',
    'user-read-email',
    'user-read-private',
    'playlist-modify-public',
    'playlist-modify-private',
}

SPOTIFY_PLAYLIST_PERMISSIONS = {
    'playlist-modify-public',
    'playlist-modify-private'
}

SPOTIFY_API_RETRIES = 5


def _get_spotify_token(grant_type: str, token: str) -> requests.Response:
    """ Fetch access token or refresh token from spotify auth api

    Args:
        grant_type (str): should be "authorization_code" to retrieve access token and "refresh_token" to refresh tokens
        token (str): authorization code to retrieve access token first time and refresh token to refresh access tokens

    Returns:
        response from the spotify authentication endpoint
    """

    client_id = current_app.config['SPOTIFY_CLIENT_ID']
    client_secret = current_app.config['SPOTIFY_CLIENT_SECRET']
    auth_header = base64.b64encode((client_id + ':' + client_secret).encode('ascii'))
    headers = {'Authorization': 'Basic %s' % auth_header.decode('ascii')}

    token_key = "refresh_token" if grant_type == "refresh_token" else "code"
    payload = {
        'redirect_uri': current_app.config['SPOTIFY_CALLBACK_URL'],
        token_key: token,
        'grant_type': grant_type,
    }

    return requests.post(OAUTH_TOKEN_URL, data=payload, headers=headers, verify=True)


class SpotifyService(ImporterService):

    def __init__(self):
        super(SpotifyService, self).__init__(ExternalServiceType.SPOTIFY)
        self.client_id = current_app.config['SPOTIFY_CLIENT_ID']
        self.client_secret = current_app.config['SPOTIFY_CLIENT_SECRET']
        self.redirect_url = current_app.config['SPOTIFY_CALLBACK_URL']

    def get_user(self, user_id: int, refresh: bool = False) -> Optional[dict]:
        """ If refresh = True, then check whether the access token has expired and refresh it
        before returning the user."""
        user = spotify.get_user(db_conn, user_id)
        if user and refresh and self.user_oauth_token_has_expired(user):
            user = self.refresh_access_token(user['user_id'], user['refresh_token'])
        return user

    def add_new_user(self, user_id: int, token: dict) -> bool:
        """Create a spotify row for a user based on OAuth access tokens

        Args:
            user_id: A flask auth `current_user.id`
            token: A spotipy access token from SpotifyOAuth.get_access_token
        """
        access_token = token['access_token']
        refresh_token = token['refresh_token']
        expires_at = int(time.time()) + token['expires_in']
        scopes = token['scope'].split()
        active = set(scopes).issuperset(SPOTIFY_IMPORT_PERMISSIONS)

        sp = spotipy.Spotify(auth=access_token)
        details = sp.current_user()
        external_user_id = details["id"]

        external_service_oauth.save_token(db_conn, user_id=user_id, service=self.service, access_token=access_token,
                                          refresh_token=refresh_token, token_expires_ts=expires_at,
                                          record_listens=active, scopes=scopes, external_user_id=external_user_id)
        return True

    def get_authorize_url(self, permissions: Sequence[str]):
        """ Returns a spotipy OAuth instance that can be used to authenticate with spotify.
        Args:
            permissions: List of permissions needed by the OAuth instance
        """
        scope = ' '.join(permissions)
        return SpotifyOAuth(self.client_id, self.client_secret,
                            redirect_uri=self.redirect_url,
                            scope=scope).get_authorize_url()

    def fetch_access_token(self, code: str):
        """ Get a valid Spotify Access token given the code.
        Returns:
            a dict with the following keys
            {
                'access_token',
                'token_type',
                'scope',
                'expires_in',
                'refresh_token',
            }
        Note: We use this function instead of spotipy's implementation because there
        is a bug in the spotipy code which leads to loss of the scope received from the
        Spotify API.
        """
        r = _get_spotify_token("authorization_code", code)
        if r.status_code != 200:
            raise ExternalServiceError(r.reason)
        return r.json()

    def refresh_access_token(self, user_id: int, refresh_token: str):
        """ Refreshes the user token for the given spotify user.
        Args:
            user_id (int): the ListenBrainz row ID of the user whose token is to be refreshed
            refresh_token (str): the refresh token to use for refreshing access token
        Returns:
            user (dict): the same user with updated tokens
        Raises:
            SpotifyAPIError: if unable to refresh spotify user token
            SpotifyInvalidGrantError: if the user has revoked authorization to spotify
        Note: spotipy eats up the json body in case of error but we need it for checking
        whether the user has revoked our authorization. hence, we use our own
        code instead of spotipy to fetch refresh token.
        """
        retries = SPOTIFY_API_RETRIES
        response = None
        while retries > 0:
            response = _get_spotify_token("refresh_token", refresh_token)

            if response.status_code == 200:
                break
            elif response.status_code == 400:
                error_body = response.json()
                if "error" in error_body and error_body["error"] == "invalid_grant":
                    raise ExternalServiceInvalidGrantError(error_body)

            response = None  # some other error occurred
            retries -= 1

        if response is None:
            raise ExternalServiceAPIError('Could not refresh API Token for Spotify user')

        response = response.json()
        access_token = response['access_token']
        if "refresh_token" in response:
            refresh_token = response['refresh_token']
        expires_at = int(time.time()) + response['expires_in']
        external_service_oauth.update_token(db_conn, user_id=user_id, service=self.service,
                                            access_token=access_token, refresh_token=refresh_token,
                                            expires_at=expires_at)
        return self.get_user(user_id)

    def revoke_user(self, user_id: int):
        """ Delete the user's connection to external service but retain
        the last import error message.

        Args:
            user_id (int): the ListenBrainz row ID of the user
        """
        external_service_oauth.delete_token(db_conn, user_id, self.service, remove_import_log=False)

    def get_user_connection_details(self, user_id: int):
        user = spotify.get_user_import_details(db_conn, user_id)
        if user:
            def date_to_iso(date):
                return date.isoformat() + "Z" if date else None

            user['latest_listened_at_iso'] = date_to_iso(user['latest_listened_at'])
            user['last_updated_iso'] = date_to_iso(user['last_updated'])
        return user
