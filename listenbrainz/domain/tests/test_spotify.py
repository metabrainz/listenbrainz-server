import time
from datetime import datetime, timezone
from unittest import mock
import spotipy

import requests_mock

import listenbrainz.db.user as db_user
from listenbrainz.domain.external_service import ExternalServiceAPIError, ExternalServiceInvalidGrantError
from listenbrainz.domain.spotify import SpotifyService, OAUTH_TOKEN_URL

from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class SpotifyServiceTestCase(NonAPIIntegrationTestCase):

    def setUp(self):
        super(SpotifyServiceTestCase, self).setUp()
        self.user_id = db_user.create(self.db_conn, 312, 'spotify_user')
        self.service = SpotifyService()
        
        with mock.patch.object(spotipy.Spotify, 'current_user', return_value={"id": "test_user_id"}):
            self.service.add_new_user(self.user_id, {
                'access_token': 'old-token',
                'refresh_token': 'old-refresh-token',
                'expires_in': 3600,
                'scope': 'user-read-currently-playing user-read-recently-played'
            })

        self.spotify_user = self.service.get_user(self.user_id)

    @mock.patch.object(spotipy.Spotify, 'current_user')
    def test_get_active_users(self, mock_current_user):
        mock_current_user.return_value = {"id": "test_user_id"}

        user_id_1 = db_user.create(self.db_conn, 333, 'user-1')
        user_id_2 = db_user.create(self.db_conn, 666, 'user-2')
        user_id_3 = db_user.create(self.db_conn, 999, 'user-3')

        self.service.add_new_user(user_id_2, {
            'access_token': 'access-token',
            'refresh_token': 'refresh-token',
            'expires_in': 3600,
            'scope': 'streaming',
        })

        self.service.add_new_user(user_id_3, {
            'access_token': 'access-token999',
            'refresh_token': 'refresh-token999',
            'expires_in': 3600,
            'scope': 'user-read-currently-playing user-read-recently-played',
        })
        self.service.update_user_import_status(user_id_3, error="add an error and check this user doesn't get selected")

        self.service.add_new_user(user_id_1, {
            'access_token': 'access-token333',
            'refresh_token': 'refresh-token333',
            'expires_in': 3600,
            'scope': 'user-read-currently-playing user-read-recently-played',
        })
        self.service.update_latest_listen_ts(user_id_1, int(time.time()))

        active_users = self.service.get_active_users_to_process()
        self.assertEqual(len(active_users), 2)
        self.assertEqual(active_users[0]['user_id'], user_id_1)
        self.assertEqual(active_users[1]['user_id'], self.user_id)

    def test_update_latest_listened_at(self):
        t = int(time.time())
        self.service.update_latest_listen_ts(self.user_id, t)
        user = self.service.get_user_connection_details(self.user_id)
        self.assertEqual(datetime.fromtimestamp(t, tz=timezone.utc), user['latest_listened_at'])

    # apparently, requests_mocker does not follow the usual order in which decorators are applied. :-(
    @requests_mock.Mocker()
    @mock.patch('time.time')
    def test_refresh_user_token(self, mock_requests, mock_time):
        mock_time.return_value = 0
        mock_requests.post(OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'tokentoken',
            'refresh_token': 'refreshtokentoken',
            'expires_in': 3600,
            'scope': '',
        })
        user = self.service.refresh_access_token(self.user_id, self.spotify_user['refresh_token'])
        self.assertEqual(self.user_id, user['user_id'])
        self.assertEqual('tokentoken', user['access_token'])
        self.assertEqual('refreshtokentoken', user['refresh_token'])
        self.assertEqual(datetime.fromtimestamp(3600, tz=timezone.utc), user['token_expires'])

    @requests_mock.Mocker()
    @mock.patch('time.time')
    def test_refresh_user_token_only_access(self, mock_requests, mock_time):
        mock_time.return_value = 0
        mock_requests.post(OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'tokentoken',
            'expires_in': 3600,
            'scope': '',
        })
        user = self.service.refresh_access_token(self.user_id, self.spotify_user['refresh_token'])
        self.assertEqual(self.user_id, user['user_id'])
        self.assertEqual('tokentoken', user['access_token'])
        self.assertEqual('old-refresh-token', user['refresh_token'])
        self.assertEqual(datetime.fromtimestamp(3600, tz=timezone.utc), user['token_expires'])

    @requests_mock.Mocker()
    def test_refresh_user_token_bad(self, mock_requests):
        mock_requests.post(OAUTH_TOKEN_URL, status_code=400, json={
            'error': 'invalid request',
            'error_description': 'invalid refresh token',
        })
        with self.assertRaises(ExternalServiceAPIError):
            self.service.refresh_access_token(self.user_id, self.spotify_user['refresh_token'])

    # apparently, requests_mocker does not follow the usual order in which decorators are applied. :-(
    @requests_mock.Mocker()
    def test_refresh_user_token_revoked(self, mock_requests):
        mock_requests.post(OAUTH_TOKEN_URL, status_code=400, json={
            'error': 'invalid_grant',
            'error_description': 'Refresh token revoked',
        })
        with self.assertRaises(ExternalServiceInvalidGrantError):
            self.service.refresh_access_token(self.user_id, self.spotify_user['refresh_token'])

    def test_remove_user(self):
        self.service.remove_user(self.user_id)
        self.assertIsNone(self.service.get_user(self.user_id))

    def test_get_user(self):
        user = self.service.get_user(self.user_id)
        self.assertEqual(user['user_id'], self.user_id)
        self.assertEqual(user['musicbrainz_id'], 'spotify_user')
        self.assertEqual(user['access_token'], 'old-token')
        self.assertEqual(user['refresh_token'], 'old-refresh-token')
        self.assertIsNotNone(user['last_updated'])

    @mock.patch.object(spotipy.Spotify, 'current_user')
    @mock.patch('time.time')
    def test_add_new_user(self, mock_time, mock_current_user):
        mock_current_user.return_value = {"id": "test_user_id"}
        mock_time.return_value = 0
        self.service.remove_user(self.user_id)
        self.service.add_new_user(self.user_id, {
            'access_token': 'access-token',
            'refresh_token': 'refresh-token',
            'expires_in': 3600,
            'scope': '',
        })
        user = self.service.get_user(self.user_id)
        self.assertEqual(self.user_id, user['user_id'])
        self.assertEqual('access-token', user['access_token'])
        self.assertEqual('refresh-token', user['refresh_token'])
        self.assertEqual("test_user_id", user["external_user_id"])
