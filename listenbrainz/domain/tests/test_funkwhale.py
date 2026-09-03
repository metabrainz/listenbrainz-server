import time
from datetime import datetime, timezone, timedelta
from unittest import mock

import requests_mock

import listenbrainz.db.user as db_user
import listenbrainz.db.funkwhale as db_funkwhale
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceInvalidGrantError
from listenbrainz.domain.funkwhale import FunkwhaleService

from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class FunkwhaleServiceTestCase(NonAPIIntegrationTestCase):

    def setUp(self):
        super(FunkwhaleServiceTestCase, self).setUp()
        self.user_id = db_user.create(self.db_conn, 412, 'funkwhale_user')
        self.service = FunkwhaleService()
        self.host_url = 'https://demo.funkwhale.audio'
        self.client_id = 'test_client_id'
        self.client_secret = 'test_client_secret'
        self.scopes = 'read'
        
        # Create a server entry  
        self.server_id = db_funkwhale.get_or_create_server(
            self.db_conn, self.host_url, self.client_id, self.client_secret, self.scopes
        )
        
        # Add a user token
        self.service.add_new_user(self.user_id, self.server_id, {
            'access_token': 'test-access-token',
            'refresh_token': 'test-refresh-token', 
            'expires_in': 3600
        })
        
        self.funkwhale_user = self.service.get_user(self.user_id, self.host_url)

    def test_get_user(self):
        """Test getting a valid user"""
        user = self.service.get_user(self.user_id, self.host_url)
        self.assertIsNotNone(user)
        self.assertEqual(user['user_id'], self.user_id)
        self.assertEqual(user['host_url'], self.host_url)
        self.assertEqual(user['access_token'], 'test-access-token')
        self.assertEqual(user['refresh_token'], 'test-refresh-token')

    def test_get_user_invalid_host(self):
        """Test getting user with invalid host URL returns None"""
        user = self.service.get_user(self.user_id, 'https://invalid.example.com')
        self.assertIsNone(user)

    def test_get_user_no_host(self):
        """Test getting user with no host URL returns None"""
        user = self.service.get_user(self.user_id, None)
        self.assertIsNone(user)

    @requests_mock.Mocker()
    def test_get_authorize_url_existing_server(self, mock_requests):
        """Test getting authorization URL for existing server"""
        url = self.service.get_authorize_url(self.host_url, ['read'])
        self.assertIn(self.host_url, url)
        self.assertIn('client_id', url)

    @requests_mock.Mocker()
    def test_get_authorize_url_new_server(self, mock_requests):
        """Test getting authorization URL for new server"""
        new_host = 'https://new.funkwhale.audio'
        mock_requests.post(f"{new_host}/api/v1/oauth/apps/", json={
            'client_id': 'new_client_id',
            'client_secret': 'new_client_secret'
        })
        
        url = self.service.get_authorize_url(new_host, ['read'])
        self.assertIn(new_host, url)
        self.assertIn('client_id', url)

    @requests_mock.Mocker()
    @mock.patch('listenbrainz.domain.funkwhale.session', {'funkwhale_host_url': 'https://demo.funkwhale.audio'})
    def test_fetch_access_token(self, mock_requests):
        """Test fetching access token"""
        mock_requests.post(f"{self.host_url}/api/v1/oauth/token/", json={
            'access_token': 'new-access-token',
            'refresh_token': 'new-refresh-token',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })
        
        token = self.service.fetch_access_token('auth_code_123')
        self.assertEqual(token['access_token'], 'new-access-token')

    @requests_mock.Mocker()
    def test_refresh_access_token(self, mock_requests):
        """Test refreshing access token"""
        server = db_funkwhale.get_server_by_host_url(self.db_conn, self.host_url)
        mock_requests.post(f"{self.host_url}/api/v1/oauth/token/", json={
            'access_token': 'refreshed-access-token',
            'refresh_token': 'refreshed-refresh-token',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })
        
        with mock.patch('time.time', return_value=0):
            user = self.service.refresh_access_token(self.user_id, server, 'old-refresh-token')
        
        self.assertIsNotNone(user)
        self.assertEqual(user['access_token'], 'refreshed-access-token')

    @requests_mock.Mocker()
    def test_refresh_access_token_invalid_grant(self, mock_requests):
        """Test refresh token with invalid grant error"""
        server = db_funkwhale.get_server_by_host_url(self.db_conn, self.host_url)
        mock_requests.post(f"{self.host_url}/api/v1/oauth/token/", json={
            'error': 'invalid_grant',
            'error_description': 'Refresh token revoked',
        }, status_code=400)
        
        with self.assertRaises(ExternalServiceInvalidGrantError):
            self.service.refresh_access_token(self.user_id, server, 'invalid-refresh-token')

    def test_revoke_user(self):
        """Test revoking user access"""
        self.service.revoke_user(self.user_id, self.host_url)
        token = db_funkwhale.get_token(self.db_conn, self.user_id, self.server_id)
        self.assertIsNone(token)

    def test_remove_user(self):
        """Test removing user completely"""
        self.service.remove_user(self.user_id)
        user = self.service.get_user(self.user_id, self.host_url)
        self.assertIsNone(user)

    @mock.patch('time.time')
    def test_add_new_user(self, mock_time):
        """Test adding a new user"""
        mock_time.return_value = 0
        new_user_id = db_user.create(self.db_conn, 413, 'new_funkwhale_user')
        
        result = self.service.add_new_user(new_user_id, self.server_id, {
            'access_token': 'new-access-token',
            'refresh_token': 'new-refresh-token',
            'expires_in': 3600
        })
        
        self.assertTrue(result)
        user = self.service.get_user(new_user_id, self.host_url)
        self.assertEqual(user['access_token'], 'new-access-token')

    def test_user_oauth_token_has_expired(self):
        """Test checking if token has expired"""
        # Test non-expired token
        future_time = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1)
        user_data = {'token_expiry': future_time}
        self.assertFalse(self.service.user_oauth_token_has_expired(user_data))
        
        # Test expired token
        past_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=1)
        user_data = {'token_expiry': past_time}
        self.assertTrue(self.service.user_oauth_token_has_expired(user_data))
