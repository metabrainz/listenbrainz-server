import time
import requests_mock
import listenbrainz.db.user as db_user

from flask import current_app

from data.model.external_service import ExternalService
from listenbrainz.domain import spotify
from listenbrainz.webserver.testing import ServerTestCase
from unittest import mock


class SpotifyDomainTestCase(ServerTestCase):

    def setUp(self):
        super(SpotifyDomainTestCase, self).setUp()
        self.user_id = db_user.create(312, 'spotify_user')
        spotify.add_new_user(self.user_id, {
            'access_token': 'old-token',
            'refresh_token': 'old-refresh-token',
            'expires_in': 3600,
            'scope': ['user-read-recently-played']
        })
        self.spotify_user = spotify.get_user(self.user_id)

    def test_none_values_for_last_updated_and_latest_listened_at(self):
        self.assertIsNone(self.spotify_user.last_updated_iso)
        self.assertIsNone(self.spotify_user.latest_listened_at_iso)

    # apparently, requests_mocker does not follow the usual order in which decorators are applied. :-(
    @requests_mock.Mocker()
    @mock.patch('time.time')
    def test_refresh_user_token(self, mock_requests, mock_time):
        mock_time.return_value = 0
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'tokentoken',
            'refresh_token': 'refreshtokentoken',
            'expires_in': 3600,
            'scope': '',
        })
        spotify.refresh_user_token(self.spotify_user)
        user = spotify.get_user(self.user_id)
        self.assertEqual(self.user_id, user.user_id)
        self.assertEqual('tokentoken', user.access_token)
        self.assertEqual('refreshtokentoken', user.refresh_token)
        self.assertEqual(3600, user.token_expires)

    @requests_mock.Mocker()
    @mock.patch('listenbrainz.domain.spotify.db_oauth.get_token')
    @mock.patch('listenbrainz.domain.spotify.db_oauth.update_token')
    def test_refresh_user_token_only_access(self, mock_requests, mock_update_token, mock_get_token):
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'tokentoken',
            'expires_in': 3600,
            'scope': '',
        })
        spotify.refresh_user_token(self.spotify_user)
        mock_update_token.assert_called_with(
            self.spotify_user.user_id,
            ExternalService.SPOTIFY,
            'tokentoken',
            'old-refresh-token',
            mock.ANY  # expires_at cannot be accurately calculated hence using mock.ANY
            # another option is using a range for expires_at and a Matcher but that seems far more work
        )
        mock_get_token.assert_called_with(self.spotify_user.user_id)

    @requests_mock.Mocker()
    def test_refresh_user_token_bad(self, mock_requests):
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=400, json={
            'error': 'invalid request',
            'error_description': 'invalid refresh token',
        })
        with self.assertRaises(spotify.SpotifyAPIError):
            spotify.refresh_user_token(self.spotify_user)

    # apparently, requests_mocker does not follow the usual order in which decorators are applied. :-(
    @requests_mock.Mocker()
    def test_refresh_user_token_revoked(self, mock_requests):
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=400, json={
            'error': 'invalid_grant',
            'error_description': 'Refresh token revoked',
        })
        with self.assertRaises(spotify.SpotifyInvalidGrantError):
            spotify.refresh_user_token(self.spotify_user)

    def test_get_spotify_oauth(self):
        func_oauth = spotify.get_spotify_oauth()
        self.assertEqual(func_oauth.client_id, current_app.config['SPOTIFY_CLIENT_ID'])
        self.assertEqual(func_oauth.client_secret, current_app.config['SPOTIFY_CLIENT_SECRET'])
        self.assertEqual(func_oauth.redirect_uri, 'http://localhost/profile/connect-spotify/callback')
        self.assertIsNone(func_oauth.scope)

        func_oauth = spotify.get_spotify_oauth(spotify.SPOTIFY_LISTEN_PERMISSIONS)
        self.assertIn('streaming', func_oauth.scope)
        self.assertIn('user-read-email', func_oauth.scope)
        self.assertIn('user-read-private', func_oauth.scope)
        self.assertIn('playlist-modify-public', func_oauth.scope)
        self.assertIn('playlist-modify-private', func_oauth.scope)
        self.assertNotIn('user-read-recently-played', func_oauth.scope)
        self.assertNotIn('user-read-currently-playing', func_oauth.scope)

        func_oauth = spotify.get_spotify_oauth(spotify.SPOTIFY_IMPORT_PERMISSIONS)
        self.assertIn('user-read-currently-playing', func_oauth.scope)
        self.assertIn('user-read-recently-played', func_oauth.scope)
        self.assertNotIn('streaming', func_oauth.scope)
        self.assertNotIn('user-read-email', func_oauth.scope)
        self.assertNotIn('user-read-private', func_oauth.scope)
        self.assertNotIn('playlist-modify-public', func_oauth.scope)
        self.assertNotIn('playlist-modify-private', func_oauth.scope)

    @mock.patch('listenbrainz.domain.spotify.db_oauth.get_token')
    def test_get_user(self, mock_db_get_user):
        t = int(time.time())
        mock_db_get_user.return_value = {
            'user_id': 1,
            'musicbrainz_id': 'spotify_user',
            'musicbrainz_row_id': 312,
            'access_token': 'token-token-token',
            'token_expires': t,
            'refresh_token': 'refresh-refresh-refresh',
            'last_updated': None,
            'latest_listened_at': None,
            'scopes': ['user-read-recently-played'],
        }

        user = spotify.get_user(1)
        self.assertIsInstance(user, spotify.Spotify)
        self.assertEqual(user.user_id, 1)
        self.assertEqual(user.musicbrainz_id, 'spotify_user')
        self.assertEqual(user.access_token, 'token-token-token')
        self.assertEqual(user.token_expires, t)
        self.assertEqual(user.last_updated, None)

    @mock.patch('listenbrainz.domain.spotify.db_oauth.delete_token')
    def test_remove_user(self, mock_delete):
        spotify.remove_user(1)
        mock_delete.assert_called_with(1)

    @mock.patch('listenbrainz.domain.spotify.db_oauth.save_token')
    @mock.patch('listenbrainz.domain.spotify.time.time')
    def test_add_new_user(self, mock_time, mock_create):
        mock_time.return_value = 0
        spotify.add_new_user(1, {
            'access_token': 'access-token',
            'refresh_token': 'refresh-token',
            'expires_in': 3600,
            'scope': [],
        })
        mock_create.assert_called_with(1, ExternalService.SPOTIFY, 'access-token', 'refresh-token', 3600, False, [])

    @mock.patch('listenbrainz.domain.spotify.db_spotify.get_active_users_to_process')
    def test_get_active_users(self, mock_get_active_users):
        t = int(time.time())
        mock_get_active_users.return_value = [
            {
                'user_id': 1,
                'musicbrainz_id': 'spotify_user',
                'musicbrainz_row_id': 312,
                'access_token': 'token-token-token',
                'token_expires': t,
                'refresh_token': 'refresh-refresh-refresh',
                'last_updated': None,
                'latest_listened_at': None,
                'scopes': ['user-read-recently-played'],
            },
            {
                'user_id': 2,
                'musicbrainz_id': 'spotify_user_2',
                'musicbrainz_row_id': 321,
                'access_token': 'token-token-token321',
                'token_expires': t + 31,
                'refresh_token': 'refresh-refresh-refresh321',
                'last_updated': None,
                'latest_listened_at': None,
                'scopes': ['user-read-recently-played'],
            },
        ]

        lst = spotify.get_active_users_to_process()
        mock_get_active_users.assert_called_once()
        self.assertEqual(len(lst), 2)
        self.assertIsInstance(lst[0], spotify.Spotify)
        self.assertIsInstance(lst[1], spotify.Spotify)
        self.assertEqual(lst[0].user_id, 1)
        self.assertEqual(lst[1].user_id, 2)

    @mock.patch('listenbrainz.domain.spotify.db_spotify.update_latest_listened_at')
    def test_update_latest_listened_at(self, mock_update_listened_at):
        t = int(time.time())
        spotify.update_latest_listened_at(1, t)
        mock_update_listened_at.assert_called_once_with(1, t)
