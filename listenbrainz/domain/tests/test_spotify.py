import time
import requests_mock
import listenbrainz.db.user as db_user

from flask import current_app

from listenbrainz.domain import spotify
from listenbrainz.tests.integration import IntegrationTestCase
from unittest import mock
from datetime import datetime, timezone


class SpotifyDomainTestCase(IntegrationTestCase):

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
        user = spotify.refresh_user_token(self.spotify_user)
        self.assertEqual(self.user_id, user.user_id)
        self.assertEqual('tokentoken', user.access_token)
        self.assertEqual('refreshtokentoken', user.refresh_token)
        self.assertEqual(datetime.fromtimestamp(3600, tz=timezone.utc), user.token_expires)

    @requests_mock.Mocker()
    @mock.patch('time.time')
    def test_refresh_user_token_only_access(self, mock_requests, mock_time):
        mock_time.return_value = 0
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'tokentoken',
            'expires_in': 3600,
            'scope': [],
        })
        user = spotify.refresh_user_token(self.spotify_user)
        self.assertEqual(self.user_id, user.user_id)
        self.assertEqual('tokentoken', user.access_token)
        self.assertEqual('old-refresh-token', user.refresh_token)
        self.assertEqual(datetime.fromtimestamp(3600, tz=timezone.utc), user.token_expires)

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
        self.assertEqual(func_oauth.redirect_uri, current_app.config['SPOTIFY_CALLBACK_URL'])
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

    def test_remove_user(self):
        spotify.remove_user(self.user_id)
        self.assertIsNone(spotify.get_user(self.user_id))

    def test_get_user(self):
        user = spotify.get_user(self.user_id)
        self.assertIsInstance(user, spotify.Spotify)
        self.assertEqual(user.user_id, self.user_id)
        self.assertEqual(user.musicbrainz_id, 'spotify_user')
        self.assertEqual(user.access_token, 'old-token')
        self.assertEqual(user.refresh_token, 'old-refresh-token')
        self.assertIsNotNone(user.last_updated)

    @mock.patch('listenbrainz.domain.spotify.time.time')
    def test_add_new_user(self, mock_time):
        mock_time.return_value = 0
        spotify.remove_user(self.user_id)
        spotify.add_new_user(self.user_id, {
            'access_token': 'access-token',
            'refresh_token': 'refresh-token',
            'expires_in': 3600,
            'scope': [],
        })
        user = spotify.get_user(self.user_id)
        self.assertEqual(self.user_id, user.user_id)
        self.assertEqual('access-token', user.access_token)
        self.assertEqual('refresh-token', user.refresh_token)

    def test_get_active_users(self):
        user_id_1 = db_user.create(666, 'user-1')
        user_id_2 = db_user.create(999, 'user-2')
        spotify.add_new_user(user_id_1, {
            'access_token': 'access-token',
            'refresh_token': 'refresh-token',
            'expires_in': 3600,
            'scope': [],
        })
        spotify.add_new_user(user_id_2, {
            'access_token': 'access-token999',
            'refresh_token': 'refresh-token999',
            'expires_in': 3600,
            'scope': [],
        })

        spotify.update_last_updated(user_id_2, error_message="add an error and check this user doesn't get selected")

        lst = spotify.get_active_users_to_process()
        self.assertEqual(len(lst), 2)
        self.assertIsInstance(lst[0], spotify.Spotify)
        self.assertIsInstance(lst[1], spotify.Spotify)
        self.assertEqual(lst[0].user_id, self.user_id)
        self.assertEqual(lst[1].user_id, user_id_1)

    def test_update_latest_listened_at(self):
        t = int(time.time())
        spotify.update_latest_listened_at(self.user_id, t)
        user = spotify.get_user(self.user_id)
        self.assertEqual(datetime.fromtimestamp(t, tz=timezone.utc), user.latest_listened_at)
