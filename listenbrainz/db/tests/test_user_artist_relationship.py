from listenbrainz.db.testing import DatabaseTestCase

import uuid
import listenbrainz.db.user as db_user
import listenbrainz.db.user_artist_relationship as db_user_artist_relationship


class UserArtistRelationshipTestCase(DatabaseTestCase):
    def setUp(self):
        super(UserArtistRelationshipTestCase, self).setUp()
        self.main_user = db_user.get_or_create(self.db_conn, 1, "failure_san")
        self.other_user = db_user.get_or_create(self.db_conn, 2, "not_failure_san")

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
        self.assertTrue(
            db_user_artist_relationship.insert(
                self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
            )
        )
        self.assertFalse(
            db_user_artist_relationship.insert(
                self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
            )
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
        self.assertFalse(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.other_user["id"],
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
        self.assertTrue(
            db_user_artist_relationship.delete(
                self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
            )
        )
        self.assertFalse(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.main_user["id"],
                self.artist_mbid_1,
            )
        )
        self.assertFalse(
            db_user_artist_relationship.delete(
                self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
            )
        )

    def test_delete_raises_value_error_for_invalid_relationship(self):
        with self.assertRaises(ValueError):
            db_user_artist_relationship.delete(
                self.db_conn, self.main_user["id"], self.artist_mbid_1, "invalidstuff"
            )

    def test_delete_nonexistent_relationship(self):
        self.assertFalse(
            db_user_artist_relationship.delete(
                self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
            )
        )
        self.assertFalse(
            db_user_artist_relationship.is_following_artist(
                self.db_conn,
                self.main_user["id"],
                self.artist_mbid_1,
            )
        )

    def test_get_followed_artist_mbids(self):
        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"]
        )
        self.assertListEqual(followed, [])

        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"]
        )
        self.assertEqual(1, len(followed))
        self.assertEqual(self.artist_mbid_1, followed[0]["artist_mbid"])

        db_user_artist_relationship.insert(
            self.db_conn, self.other_user["id"], self.artist_mbid_2, "follow"
        )
        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"]
        )
        self.assertEqual(1, len(followed))

        # most recently followed first
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_2, "follow"
        )
        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"]
        )
        self.assertListEqual(
            [self.artist_mbid_2, self.artist_mbid_1],
            [row["artist_mbid"] for row in followed],
        )

    def test_get_followed_artist_mbids_pagination(self):
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_2, "follow"
        )

        # limit to 1, returns only the most recent follow
        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"], limit=1
        )
        self.assertListEqual([self.artist_mbid_2], [row["artist_mbid"] for row in followed])

        followed = db_user_artist_relationship.get_followed_artist_mbids(
            self.db_conn, self.main_user["id"], limit=50, offset=1
        )
        self.assertListEqual([self.artist_mbid_1], [row["artist_mbid"] for row in followed])

    def test_get_users_following_artist(self):
        followers = db_user_artist_relationship.get_users_following_artist(
            self.db_conn, self.artist_mbid_1
        )
        self.assertListEqual(followers, [])

        db_user_artist_relationship.insert(
            self.db_conn, self.main_user["id"], self.artist_mbid_1, "follow"
        )
        followers = db_user_artist_relationship.get_users_following_artist(
            self.db_conn, self.artist_mbid_1
        )
        self.assertEqual(1, len(followers))
        self.assertEqual(self.main_user["id"], followers[0]["user_id"])

        db_user_artist_relationship.insert(
            self.db_conn, self.other_user["id"], self.artist_mbid_1, "follow"
        )
        followers = db_user_artist_relationship.get_users_following_artist(
            self.db_conn, self.artist_mbid_1
        )
        self.assertEqual(2, len(followers))
        returned_user_ids = {row["user_id"] for row in followers}
        self.assertSetEqual(
            returned_user_ids, {self.main_user["id"], self.other_user["id"]}
        )
