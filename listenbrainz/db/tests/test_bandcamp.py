from listenbrainz.db import bandcamp as db_bandcamp
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase


class BandcampDBTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.host_url = "https://bandcamp.example.com"
        self.user = db_user.get_or_create(self.db_conn, 1, "testbandcampuser")

    def test_save_and_get_user_token(self):
        token_id = db_bandcamp.save_user_token(
            self.db_conn,
            user_id=self.user["id"],
            host_url=self.host_url,
            username="testuser",
            encrypted_password="encrypted_test_password"
        )
        token = db_bandcamp.get_user_token(self.db_conn, user_id=self.user["id"])

        self.assertEqual(token_id, token["id"])
        self.assertEqual(token["username"], "testuser")
        self.assertEqual(token["encrypted_password"], "encrypted_test_password")

    def test_save_user_token_updates_existing_user_token(self):
        first_token_id = db_bandcamp.save_user_token(
            self.db_conn,
            user_id=self.user["id"],
            host_url=self.host_url,
            username="testuser",
            encrypted_password="encrypted_test_password"
        )
        second_token_id = db_bandcamp.save_user_token(
            self.db_conn,
            user_id=self.user["id"],
            host_url="https://another.example.com",
            username="updateduser",
            encrypted_password="updated_encrypted_test_password"
        )

        token = db_bandcamp.get_user_token(self.db_conn, user_id=self.user["id"])
        self.assertEqual(first_token_id, second_token_id)
        self.assertEqual(token["username"], "updateduser")
        self.assertEqual(token["encrypted_password"], "updated_encrypted_test_password")

    def test_delete_user_token(self):
        db_bandcamp.save_user_token(
            self.db_conn,
            user_id=self.user["id"],
            host_url=self.host_url,
            username="testuser",
            encrypted_password="encrypted_test_password"
        )

        db_bandcamp.delete_user_token(self.db_conn, user_id=self.user["id"])

        token = db_bandcamp.get_user_token(self.db_conn, user_id=self.user["id"])
        self.assertIsNone(token)
