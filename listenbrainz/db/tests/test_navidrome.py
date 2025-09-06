import unittest
from unittest.mock import patch, MagicMock

from listenbrainz.db import navidrome as db_navidrome
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver import create_app


class NavidromeDBTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.app = create_app()
        self.host_url = "https://navidrome.example.com"
        
        # Create a test user
        self.user = db_user.get_or_create(self.db_conn, 1, 'testnavidromeuser')

    def test_get_or_create_server(self):
        """Test getting or creating a Navidrome server"""
        with self.app.app_context():
            # Test creating a new server
            server_id = db_navidrome.get_or_create_server(
                self.db_conn,
                host_url=self.host_url
            )
            
            self.assertIsNotNone(server_id)
            self.assertIsInstance(server_id, int)
            
            # Test getting existing server returns same ID
            existing_server_id = db_navidrome.get_or_create_server(
                self.db_conn,
                host_url=self.host_url
            )
            
            self.assertEqual(server_id, existing_server_id)

    def test_save_user_token(self):
        """Test saving user token for Navidrome"""
        with self.app.app_context():
            # Save user token (using host_url, not server_id)
            token_id = db_navidrome.save_user_token(
                self.db_conn,
                user_id=self.user['id'],
                host_url=self.host_url,
                username="testuser",
                encrypted_password="encrypted_password_123"
            )
            
            self.assertTrue(token_id)
            self.assertIsInstance(token_id, int)

    def test_get_user_token(self):
        """Test retrieving user token for Navidrome"""
        with self.app.app_context():
            # Save token first
            db_navidrome.save_user_token(
                self.db_conn,
                user_id=self.user['id'],
                host_url=self.host_url,
                username="testuser",
                encrypted_password="encrypted_test_password"
            )
            
            # Retrieve token
            token = db_navidrome.get_user_token(self.db_conn, user_id=self.user['id'])
            
            self.assertIsNotNone(token)
            self.assertEqual(token['username'], "testuser")
            self.assertEqual(token['encrypted_password'], "encrypted_test_password")
            self.assertEqual(token['host_url'], self.host_url)

    def test_delete_user_token(self):
        """Test deleting user token for Navidrome"""
        with self.app.app_context():
            # Save token first
            db_navidrome.save_user_token(
                self.db_conn,
                user_id=self.user['id'],
                host_url=self.host_url,
                username="testuser",
                encrypted_password="encrypted_test_password"
            )
            
            # Delete token
            db_navidrome.delete_user_token(self.db_conn, user_id=self.user['id'])
            
            # Verify token is deleted
            token = db_navidrome.get_user_token(self.db_conn, user_id=self.user['id'])
            self.assertIsNone(token)

    def test_get_server_by_host_url(self):
        """Test retrieving server by host URL"""
        with self.app.app_context():
            # Create a server
            db_navidrome.get_or_create_server(
                self.db_conn,
                host_url=self.host_url
            )
            
            # Retrieve by host URL
            server = db_navidrome.get_server_by_host_url(
                self.db_conn,
                self.host_url
            )
            
            self.assertIsNotNone(server)
            self.assertEqual(server['host_url'], self.host_url)

    def test_get_server_by_host_url_not_found(self):
        """Test retrieving non-existent server returns None"""
        with self.app.app_context():
            server = db_navidrome.get_server_by_host_url(
                self.db_conn,
                "https://nonexistent.example.com"
            )
            
            self.assertIsNone(server)

    def test_user_token_with_server_relationship(self):
        """Test that user token correctly references server"""
        with self.app.app_context():
            # Save user token
            db_navidrome.save_user_token(
                self.db_conn,
                user_id=self.user['id'],
                host_url=self.host_url,
                username="testuser",
                encrypted_password="encrypted_test_password"
            )
            
            # Get token with server info
            token = db_navidrome.get_user_token(self.db_conn, user_id=self.user['id'])
            
            # Check that the token contains the host URL from the server
            self.assertEqual(token['host_url'], self.host_url)
