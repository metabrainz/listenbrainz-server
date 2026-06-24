from listenbrainz.db.testing import DatabaseTestCase

import uuid
import listenbrainz.db.user as db_user
import listenbrainz.db.user_artist_relationship as db_user_artist_relationship


class UserArtistRelationshipTestCase(DatabaseTestCase):
    def setUp(self):
        super(UserArtistRelationshipTestCase, self).setUp()
        self.main_user = db_user.get_or_create(self.db_conn, 1, "failure_san")
        self.other_user = db_user.get_or_create(self.db_conn, 2, "not_failure_san")

        # sample artist MBIDs (not real, just valid UUIDs for testing)
        self.artist_mbid_1 = str(uuid.uuid4())
        self.artist_mbid_2 = str(uuid.uuid4())

    def test_insert(self):
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        self.assertTrue(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.main_user["id"],
                self.artist_mbid_1,
            )
        )

    def test_insert_idempotent(self):
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        # second insert should do nothing
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        self.assertTrue(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.main_user["id"],
                self.artist_mbid_1,
            )
        )

    def test_insert_raises_value_error_for_invalid_relationship(self):
        with self.assertRaises(ValueError):
            db_user_artist_relationship.insert(
                self.db_conn, self.main_user["id"], self.artist_mbid_1, "invalidstuff"
            )

    def test_is_following_artist(self):
        self.assertFalse(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.main_user["id"],
                self.artist_mbid_1,
            )
        )
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        self.assertTrue(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.main_user["id"],
                self.artist_mbid_1,
            )
        )

    def test_delete(self):
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        self.assertTrue(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.main_user["id"],
                self.artist_mbid_1,
            )
        )
        db_user_artist_relationship.delete(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        self.assertFalse(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.main_user["id"],
                self.artist_mbid_1,
            )
        )

    def test_delete_raises_value_error_for_invalid_relationship(self):
        with self.assertRaises(ValueError):
            db_user_artist_relationship.delete(
                self.db_conn, self.main_user["id"], self.artist_mbid_1, "invalidstuff"
            )

    def test_get_followed_artist_mbids(self):
        # no follows yet, should return an empty list
        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"]
        )
        self.assertListEqual(followed, [])

        # follow one artist
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"]
        )
        self.assertEqual(1, len(followed))

        # follow a second artist
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_2, "follow"
        )
        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"]
        )
        self.assertEqual(2, len(followed))

    def test_get_users_following_artist(self):
        # no followers yet
        followers = db_user_artist_relationship.get_users_following_artist(
            self.db_conn, self.artist_mbid_1
        )
        self.assertListEqual(followers, [])

        # one user follows the artist
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        followers = db_user_artist_relationship.get_users_following_artist(
            self.db_conn, self.artist_mbid_1
        )
        self.assertEqual(1, len(followers))

        # a second user follows the same artist
        db_user_artist_relationship.insert(
            self.db_conn, self.other_user["id"], self.artist_mbid_1, "follow"
        )
        followers = db_user_artist_relationship.get_users_following_artist(
            self.db_conn, self.artist_mbid_1
        )
        self.assertEqual(2, len(followers))
