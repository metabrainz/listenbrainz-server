import unittest
from datetime import datetime, timedelta, timezone

import listenbrainz.db.user as db_user
import listenbrainz.db.funkwhale as db_funkwhale
from listenbrainz.db.testing import DatabaseTestCase


class FunkwhaleDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.host_url = "https://demo.funkwhale.audio"
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.scopes = "read write:favorites"

        # Create a test user
        self.user = db_user.get_or_create(self.db_conn, 1, 'testfunkwhaleuser')

        # Create a test server
        self.server_id = db_funkwhale.get_or_create_server(
            self.db_conn, self.host_url, self.client_id, self.client_secret, self.scopes
        )

    def test_get_or_create_server(self):
        """Test creating and retrieving a server"""
        server = db_funkwhale.get_server_by_host_url(self.db_conn, self.host_url)
        self.assertIsNotNone(server)
        self.assertEqual(server['host_url'], self.host_url)
        self.assertEqual(server['client_id'], self.client_id)
        self.assertEqual(server['scopes'], self.scopes)

    def test_save_and_get_token(self):
        """Test saving and retrieving a token"""
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Save token
        token_id = db_funkwhale.save_token(
            self.db_conn, self.user['id'], self.server_id, 'access_token_123', 'refresh_token_123', expiry
        )
        self.assertIsNotNone(token_id)
        
        # Get token
        token = db_funkwhale.get_token(self.db_conn, self.user['id'], self.server_id)
        self.assertIsNotNone(token)
        self.assertEqual(token['access_token'], 'access_token_123')
        self.assertEqual(token['refresh_token'], 'refresh_token_123')

    def test_update_token(self):
        """Test updating an existing token"""
        expiry1 = datetime.now(timezone.utc) + timedelta(hours=1)
        expiry2 = datetime.now(timezone.utc) + timedelta(hours=2)
        
        # Create initial token
        db_funkwhale.save_token(
            self.db_conn, self.user['id'], self.server_id, 'old_token', 'old_refresh', expiry1
        )
        
        # Update the token
        db_funkwhale.update_token(
            self.db_conn, self.user['id'], self.server_id, 'new_token', 'new_refresh', expiry2
        )
        
        # Verify update
        token = db_funkwhale.get_token(self.db_conn, self.user['id'], self.server_id)
        self.assertEqual(token['access_token'], 'new_token')
        self.assertEqual(token['refresh_token'], 'new_refresh')

    def test_delete_token(self):
        """Test deleting a token"""
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Create a token
        db_funkwhale.save_token(
            self.db_conn, self.user['id'], self.server_id, 'access_token', 'refresh_token', expiry
        )
        
        # Verify token exists
        token = db_funkwhale.get_token(self.db_conn, self.user['id'], self.server_id)
        self.assertIsNotNone(token)
        
        # Delete the token
        db_funkwhale.delete_token(self.db_conn, self.user['id'], self.server_id)
        
        # Verify token was deleted
        token = db_funkwhale.get_token(self.db_conn, self.user['id'], self.server_id)
        self.assertIsNone(token)

    def test_get_nonexistent_token(self):
        """Test getting a non-existent token returns None"""
        token = db_funkwhale.get_token(self.db_conn, 999, self.server_id)
        self.assertIsNone(token)

    def test_get_nonexistent_server(self):
        """Test getting a non-existent server returns None"""
        server = db_funkwhale.get_server_by_host_url(self.db_conn, 'https://nonexistent.example.com')
        self.assertIsNone(server)
