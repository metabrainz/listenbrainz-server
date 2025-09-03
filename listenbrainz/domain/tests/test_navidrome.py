import unittest
from unittest.mock import patch, MagicMock
import hashlib
import time

from listenbrainz.domain.navidrome import NavidromeService
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import create_app


class NavidromeServiceTestCase(IntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.app = create_app()

    def test_generate_auth_params(self):
        """Test MD5 authentication parameter generation"""
        with self.app.app_context():
            service = NavidromeService()
            password = "testpassword"
            
            auth_params = service._generate_auth_params("testuser", password)
            
            self.assertEqual(auth_params['username'], "testuser")
            self.assertIn('token', auth_params)
            self.assertIn('salt', auth_params)
            
            # Verify the token is MD5 hash of password + salt
            expected_token = hashlib.md5((password + auth_params['salt']).encode()).hexdigest()
            self.assertEqual(auth_params['token'], expected_token)

    @patch('listenbrainz.domain.navidrome.requests.get')
    def test_authenticate_success(self, mock_get):
        """Test successful authentication to Navidrome server"""
        # Mock successful ping response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subsonic-response": {
                "status": "ok",
                "version": "1.16.1",
                "type": "navidrome",
                "serverVersion": "0.49.3"
            }
        }
        mock_get.return_value = mock_response

        with self.app.app_context():
            service = NavidromeService()
            result = service.authenticate(
                "https://navidrome.example.com",
                "testuser",
                "testpassword"
            )
            
            self.assertIsNotNone(result)
            self.assertEqual(result['host_url'], "https://navidrome.example.com")
            self.assertEqual(result['username'], "testuser")
            self.assertIn('encrypted_password', result)
            self.assertEqual(result['server_version'], '1.16.1')

    @patch('listenbrainz.domain.navidrome.requests.get')
    def test_authenticate_invalid_credentials(self, mock_get):
        """Test authentication with invalid credentials"""
        # Mock authentication failure response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subsonic-response": {
                "status": "failed",
                "error": {
                    "code": 40,
                    "message": "Wrong username or password"
                }
            }
        }
        mock_get.return_value = mock_response

        with self.app.app_context():
            service = NavidromeService()
            with self.assertRaises(ExternalServiceError) as context:
                service.authenticate(
                    "https://navidrome.example.com",
                    "testuser",
                    "wrongpassword"
                )
            
            self.assertIn("Wrong username or password", str(context.exception))

    @patch('listenbrainz.domain.navidrome.requests.get')
    def test_authenticate_server_error(self, mock_get):
        """Test authentication with server error"""
        # Mock server error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")
        mock_get.return_value = mock_response

        with self.app.app_context():
            service = NavidromeService()
            with self.assertRaises(ExternalServiceError) as context:
                service.authenticate(
                    "https://navidrome.example.com",
                    "testuser",
                    "testpassword"
                )
            
            self.assertIn("Authentication error", str(context.exception))

    @patch('listenbrainz.domain.navidrome.requests.get')
    def test_authenticate_invalid_url(self, mock_get):
        """Test authentication with invalid server URL"""
        # Mock connection error
        mock_get.side_effect = Exception("Connection failed")

        with self.app.app_context():
            service = NavidromeService()
            with self.assertRaises(ExternalServiceError) as context:
                service.authenticate(
                    "https://invalid.example.com",
                    "testuser",
                    "testpassword"
                )
            
            self.assertIn("Authentication error", str(context.exception))

    @patch('listenbrainz.db.navidrome.save_user_token')
    @patch('listenbrainz.domain.navidrome.NavidromeService.authenticate')
    def test_connect_user_success(self, mock_auth, mock_save_token):
        """Test successful user connection"""
        # Mock authentication response
        mock_auth.return_value = {
            "host_url": "https://navidrome.example.com",
            "username": "testuser",
            "encrypted_password": "encrypted_pass",
            "server_version": "0.49.3"
        }

        # Mock token saving - returns token_id
        mock_save_token.return_value = 123

        with self.app.app_context():
            service = NavidromeService()
            result = service.connect_user(
                user_id=1,
                host_url="https://navidrome.example.com",
                username="testuser",
                password="testpassword"
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['host_url'], "https://navidrome.example.com")
            self.assertEqual(result['username'], "testuser")
            self.assertEqual(result['server_version'], "0.49.3")
            self.assertEqual(result['token_id'], 123)

            mock_auth.assert_called_once()
            mock_save_token.assert_called_once()

    @patch('listenbrainz.domain.navidrome.NavidromeService.authenticate')
    def test_connect_user_auth_failure(self, mock_auth):
        """Test user connection with authentication failure"""
        # Mock authentication failure
        mock_auth.side_effect = ExternalServiceAPIError("Wrong username or password")

        with self.app.app_context():
            service = NavidromeService()
            with self.assertRaises(ExternalServiceAPIError) as context:
                service.connect_user(
                    user_id=1,
                    host_url="https://navidrome.example.com",
                    username="testuser",
                    password="wrongpassword"
                )
            
            self.assertIn("Wrong username or password", str(context.exception))