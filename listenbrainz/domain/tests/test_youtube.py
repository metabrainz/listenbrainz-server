import time
from datetime import datetime, timezone
from unittest import mock

import requests_mock

import listenbrainz.db.user as db_user
from listenbrainz.domain.external_service import ExternalServiceAPIError, ExternalServiceInvalidGrantError
from listenbrainz.domain.youtube import YoutubeService, OAUTH_TOKEN_URL, YOUTUBE_SCOPES

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
        self.assertEqual(self.youtube_user['youtube_user'], user['refresh_token'])
        self.assertEqual(datetime.fromtimestamp(3920, tz=timezone.utc), user['token_expires'])


