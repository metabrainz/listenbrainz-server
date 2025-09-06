import hashlib
from unittest.mock import patch

import requests_mock

from listenbrainz.db import user as db_user
from listenbrainz.db import navidrome as db_navidrome
from listenbrainz.domain.navidrome import NavidromeService
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import create_app


class NavidromeServiceTestCase(IntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.app = create_app()
        self.app.config["NAVIDROME_ENCRYPTION_KEY"] = "cpoJ8jX49UZD7XhUxF9d8wV4_CkyCcHpIlzG-PawZds="
        self.user = db_user.get_or_create(self.db_conn, 12354, "navidrome_user")

    @requests_mock.Mocker()
    def test_authenticate_success(self, mock_requests):
        """Test successful authentication to Navidrome server"""
        mock_requests.get(
            "https://demo.navidrome.org/rest/ping",
            status_code=200,
            json={
                "subsonic-response": {
                    "status": "ok",
                    "version": "1.16.1",
                    "type": "navidrome",
                    "serverVersion": "0.49.3"
                }
            }
        )
        password = "testpassword"
        with self.app.app_context():
            service = NavidromeService()
            encrypted = service.authenticate(
                "https://demo.navidrome.org", "testuser", password
            )
            self.assertEqual(service._decrypt_password(encrypted), password)

    @requests_mock.Mocker()
    def test_authenticate_invalid_credentials(self, mock_requests):
        """Test authentication with invalid credentials"""
        mock_requests.get(
            "https://demo.navidrome.org/rest/ping",
            status_code=200,
            json={
                "subsonic-response": {
                    "status": "failed",
                    "error": {
                        "code": 40,
                        "message": "Wrong username or password"
                    }
                }
            }
        )

        with self.app.app_context():
            service = NavidromeService()
            with self.assertRaises(ExternalServiceError) as context:
                service.authenticate(
                    "https://demo.navidrome.org/rest/ping",
                    "testuser",
                    "wrongpassword"
                )
            self.assertIn("Wrong username or password", str(context.exception))

    @requests_mock.Mocker()
    def test_connect_user_success(self, mock_requests):
        """Test successful user connection"""
        mock_requests.get(
            "https://demo.navidrome.org/rest/ping",
            status_code=200,
            json={
                "subsonic-response": {
                    "status": "ok",
                    "version": "1.16.1",
                    "type": "navidrome",
                    "serverVersion": "0.49.3"
                }
            }
        )

        with self.app.app_context():
            service = NavidromeService()
            token_id = service.connect_user(
                user_id=self.user["id"],
                host_url="https://demo.navidrome.org",
                username="testuser",
                password="testpassword"
            )
            result = db_navidrome.get_user_token(self.db_conn, user_id=self.user["id"])
            self.assertEqual(token_id, result["id"])
            self.assertEqual(result["host_url"], "https://demo.navidrome.org")
            self.assertEqual(result["username"], "testuser")
            self.assertEqual(
                service._decrypt_password(result["encrypted_password"]),
                "testpassword"
            )

    @patch.object(NavidromeService, "authenticate")
    def test_connect_user_auth_failure(self, mock_navidrome):
        """Test user connection with authentication failure"""
        mock_navidrome.side_effect = ExternalServiceAPIError("Wrong username or password")
        with self.app.app_context():
            service = NavidromeService()
            with self.assertRaises(ExternalServiceAPIError) as context:
                service.connect_user(
                    user_id=self.user["id"],
                    host_url="https://demo.navidrome.org",
                    username="testuser",
                    password="wrongpassword"
                )
            self.assertIn("Wrong username or password", str(context.exception))

    @requests_mock.Mocker()
    def test_get_and_delete_user(self, mock_requests):
        """Test retrieving user token for Navidrome"""
        mock_requests.get(
            "https://demo.navidrome.org/rest/ping",
            status_code=200,
            json={
                "subsonic-response": {
                    "status": "ok",
                    "version": "1.16.1",
                    "type": "navidrome",
                    "serverVersion": "0.49.3"
                }
            }
        )
        with self.app.app_context():
            service = NavidromeService()
            self.assertIsNone(service.get_user(self.user["id"]))

            password = "testpassword"
            service.connect_user(
                self.user["id"],
                "https://demo.navidrome.org",
                "testuser",
                password
            )
            result = service.get_user(self.user["id"])
            self.assertIsNotNone(result)

            self.assertEqual(result["instance_url"], "https://demo.navidrome.org")
            self.assertEqual(result["username"], "testuser")
            self.assertIsNotNone(result["md5_auth_token"])
            self.assertIsNotNone(result["salt"])

            self.assertEqual(
                result["md5_auth_token"],
                hashlib.md5((password + result["salt"]).encode("utf-8")).hexdigest()
            )

            result = service.get_user(self.user["id"], include_token=False)
            self.assertEqual(result["instance_url"], "https://demo.navidrome.org")
            self.assertEqual(result["username"], "testuser")
            self.assertIsNone(result["md5_auth_token"])
            self.assertIsNone(result["salt"])

            service.remove_user(self.user["id"])
            self.assertIsNone(service.get_user(self.user["id"]))
