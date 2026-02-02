from unittest import mock

import requests_mock

import listenbrainz.db.user as db_user
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService, OAUTH_TOKEN_URL
from listenbrainz.domain.external_service import ExternalServiceInvalidGrantError

from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class CritiqueBrainzTestCase(NonAPIIntegrationTestCase):

    def setUp(self):
        super(CritiqueBrainzTestCase, self).setUp()
        self.user_id = db_user.create(self.db_conn, 211, 'critiquebrainz_user')
        self.service = CritiqueBrainzService()
        self.service.add_new_user(self.user_id, {
            'access_token': 'access-token',
            'expires_in': 3599,
            'refresh_token': 'refresh-token',
            'token_type': 'Bearer'
        })
        self.critiquebrainz_user = self.service.get_user(self.user_id)

    def test_get_user(self):
        user = self.service.get_user(self.user_id)
        self.assertEqual(user['user_id'], self.user_id)
        self.assertEqual(user['musicbrainz_id'], 'critiquebrainz_user')
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
            "refresh_token": "a-refresh-token",
            "token_type": "Bearer"
        })

        user = self.service.refresh_access_token(self.user_id, self.critiquebrainz_user['refresh_token'])
        self.assertEqual(self.user_id, user['user_id'])
        self.assertEqual('new-access-token', user['access_token'])
        self.assertEqual('a-refresh-token', user['refresh_token'])

    @requests_mock.Mocker()
    def test_refresh_user_token_revoked(self, mock_requests):
        mock_requests.post(OAUTH_TOKEN_URL, status_code=400, json={
            'error': 'invalid_grant',
            'error_description': 'Token is expired or revoked.',
        })
        with self.assertRaises(ExternalServiceInvalidGrantError):
            self.service.refresh_access_token(self.user_id, self.critiquebrainz_user['refresh_token'])

    @requests_mock.Mocker()
    def test_fetch_access_token(self, mock_requests):
        response = {
            "access_token": "new-access-token",
            "expires_in": 3920,
            "refresh_token": "valid-refresh-token",
            "token_type": "Bearer"
        }

        mock_requests.post(OAUTH_TOKEN_URL, status_code=200, json=response)
        token = self.service.fetch_access_token("valid-code")
        self.assertEqual("new-access-token", token["access_token"])
        self.assertEqual("valid-refresh-token", token["refresh_token"])
        self.assertEqual(3920, token["expires_in"])
