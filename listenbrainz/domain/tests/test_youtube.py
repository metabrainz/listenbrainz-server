import time
from datetime import datetime, timezone
from unittest import mock

import requests_mock

import listenbrainz.db.user as db_user
from listenbrainz.domain.external_service import ExternalServiceAPIError, ExternalServiceInvalidGrantError
from listenbrainz.domain.youtube import YoutubeService, OAUTH_TOKEN_URL, YOUTUBE_SCOPES, OAUTH_REVOKE_URL

from listenbrainz.tests.integration import IntegrationTestCase


class YoutubeServiceTestCase(IntegrationTestCase):

    def setUp(self):
        super(YoutubeServiceTestCase, self).setUp()
        self.user_id = db_user.create(211, 'youtube_user')
        self.service = YoutubeService()
        self.service.add_new_user(self.user_id, {
            'access_token': 'access-token',
            'expires_at': time.time() + 3599,
            'expires_in': 3599,
            'refresh_token': 'refresh-token',
            'scope': YOUTUBE_SCOPES,
            'token_type': 'Bearer'
        })
        self.youtube_user = self.service.get_user(self.user_id)

    def test_get_user(self):
        user = self.service.get_user(self.user_id)
        self.assertIsInstance(user, dict)
        self.assertEqual(user['user_id'], self.user_id)
        self.assertEqual(user['musicbrainz_id'], 'youtube_user')
        self.assertEqual(user['access_token'], 'access-token')
        self.assertEqual(user['refresh_token'], 'refresh-token')
        self.assertIsNotNone(user['last_updated'])

    @requests_mock.Mocker()
    @mock.patch('time.time')
    def test_refresh_access_token(self, mock_requests, mock_time):
        mock_time.return_value = 0
        mock_requests.post(OAUTH_TOKEN_URL, status_code=200, json={
            "access_token": "new-access-token",
            "expires_in": 3920,
            "scope": YOUTUBE_SCOPES[0],
            "token_type": "Bearer"
        })

        user = self.service.refresh_access_token(self.user_id, self.youtube_user['refresh_token'])
        self.assertEqual(self.user_id, user['user_id'])
        self.assertEqual('new-access-token', user['access_token'])
        self.assertEqual(self.youtube_user['refresh_token'], user['refresh_token'])

    @requests_mock.Mocker()
    def test_refresh_user_token_revoked(self, mock_requests):
        mock_requests.post(OAUTH_TOKEN_URL, status_code=400, json={
            'error': 'invalid_grant',
            'error_description': 'Token is expired or revoked.',
        })
        with self.assertRaises(ExternalServiceInvalidGrantError):
            self.service.refresh_access_token(self.user_id, self.youtube_user['refresh_token'])

    @requests_mock.Mocker()
    def test_fetch_access_token(self, mock_requests):
        response = {
            "access_token": "new-access-token",
            "expires_in": 3920,
            "scope": YOUTUBE_SCOPES[0],
            "refresh_token": "valid-refresh-token",
            "token_type": "Bearer"
        }

        mock_requests.post(OAUTH_TOKEN_URL, status_code=200, json=response)
        token = self.service.fetch_access_token("valid-code")
        self.assertEqual("new-access-token", token["access_token"])
        self.assertEqual("valid-refresh-token", token["refresh_token"])
        self.assertEqual(3920, token["expires_in"])
        self.assertEqual(YOUTUBE_SCOPES, token["scope"])

    @requests_mock.Mocker()
    def test_remove_user(self, mock_requests):
        mock_requests.post(OAUTH_REVOKE_URL, status_code=200, json={})
        self.service.remove_user(self.user_id)
        self.assertIsNone(self.service.get_user(self.user_id))
        self.assertTrue(mock_requests.called_once)

    @requests_mock.Mocker()
    def test_remove_user_revoke_fail(self, mock_requests):
        mock_requests.post(OAUTH_REVOKE_URL, status_code=400, json={"error": "invalid token"})
        self.service.remove_user(self.user_id)
        self.assertIsNone(self.service.get_user(self.user_id))
        self.assertTrue(mock_requests.called_once)
