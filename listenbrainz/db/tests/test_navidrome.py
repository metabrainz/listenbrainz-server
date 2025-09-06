from listenbrainz.db import navidrome as db_navidrome
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase


class NavidromeDBTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.host_url = "https://navidrome.example.com"
        self.user = db_user.get_or_create(self.db_conn, 1, "testnavidromeuser")

    def test_get_or_create_server(self):
        """Test getting or creating a Navidrome server"""
        server_id = db_navidrome.get_or_create_server(
            self.db_conn,
            host_url=self.host_url
        )
        self.assertIsNotNone(server_id)
        self.assertIsInstance(server_id, int)

        existing_server_id = db_navidrome.get_or_create_server(
            self.db_conn,
            host_url=self.host_url
        )
        self.assertEqual(server_id, existing_server_id)

    def test_save_user_token(self):
        """Test saving user token for Navidrome"""
        token_id = db_navidrome.save_user_token(
            self.db_conn,
            user_id=self.user["id"],
            host_url=self.host_url,
            username="testuser",
            encrypted_password="encrypted_password_123"
        )
        self.assertTrue(token_id)
        self.assertIsInstance(token_id, int)

    def test_get_user_token(self):
        """Test retrieving user token for Navidrome"""
        db_navidrome.save_user_token(
            self.db_conn,
            user_id=self.user["id"],
            host_url=self.host_url,
            username="testuser",
            encrypted_password="encrypted_test_password"
        )

        token = db_navidrome.get_user_token(self.db_conn, user_id=self.user["id"])

        self.assertIsNotNone(token)
        self.assertEqual(token["username"], "testuser")
        self.assertEqual(token["encrypted_password"], "encrypted_test_password")
        self.assertEqual(token["host_url"], self.host_url)

    def test_delete_user_token(self):
        """Test deleting user token for Navidrome"""
        db_navidrome.save_user_token(
            self.db_conn,
            user_id=self.user["id"],
            host_url=self.host_url,
            username="testuser",
            encrypted_password="encrypted_test_password"
        )

        db_navidrome.delete_user_token(self.db_conn, user_id=self.user["id"])

        token = db_navidrome.get_user_token(self.db_conn, user_id=self.user["id"])
        self.assertIsNone(token)

    def test_get_server_by_host_url(self):
        """Test retrieving server by host URL"""
        db_navidrome.get_or_create_server(
            self.db_conn,
            host_url=self.host_url
        )
        server = db_navidrome.get_server_by_host_url(
            self.db_conn,
            self.host_url
        )
        self.assertIsNotNone(server)
        self.assertEqual(server["host_url"], self.host_url)

    def test_get_server_by_host_url_not_found(self):
        """Test retrieving non-existent server returns None"""
        server = db_navidrome.get_server_by_host_url(
            self.db_conn,
            "https://nonexistent.example.com"
        )
        self.assertIsNone(server)

    def test_user_token_with_server_relationship(self):
        """Test that user token correctly references server"""
        db_navidrome.save_user_token(
            self.db_conn,
            user_id=self.user["id"],
            host_url=self.host_url,
            username="testuser",
            encrypted_password="encrypted_test_password"
        )
        token = db_navidrome.get_user_token(self.db_conn, user_id=self.user["id"])
        self.assertEqual(token["host_url"], self.host_url)
