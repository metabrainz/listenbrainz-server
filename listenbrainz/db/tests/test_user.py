import json

import listenbrainz.db.user as db_user
import listenbrainz.db.external_service_oauth as db_oauth
import sqlalchemy

from data.model.external_service import ExternalServiceType
from listenbrainz.db.similar_users import import_user_similarities
from listenbrainz.db.testing import DatabaseTestCase


class UserTestCase(DatabaseTestCase):

    def test_create(self):
        user_id = db_user.create(self.db_conn, 0, "izzy_cheezy")
        self.assertIsNotNone(db_user.get(self.db_conn, user_id))

    def test_get_by_musicbrainz_row_id(self):
        user_id = db_user.create(self.db_conn, 0, 'frank')
        user = db_user.get_by_mb_row_id(self.db_conn, 0)
        self.assertEqual(user['id'], user_id)
        user = db_user.get_by_mb_row_id(self.db_conn, 0, musicbrainz_id='frank')
        self.assertEqual(user['id'], user_id)

    def test_update_token(self):
        user = db_user.get_or_create(self.db_conn, 1, 'testuserplsignore')
        old_token = user['auth_token']
        db_user.update_token(self.db_conn, user['id'])
        user = db_user.get_by_mb_id(self.db_conn, 'testuserplsignore')
        self.assertNotEqual(old_token, user['auth_token'])

    def test_update_last_login(self):
        """ Tests db.user.update_last_login """

        user = db_user.get_or_create(self.db_conn, 2, 'testlastloginuser')

        # set the last login value of the user to 0
        self.db_conn.execute(sqlalchemy.text("""
            UPDATE "user"
               SET last_login = to_timestamp(0)
             WHERE id = :id
        """), {
            'id': user['id']
        })

        user = db_user.get(self.db_conn, user['id'])
        self.assertEqual(int(user['last_login'].strftime('%s')), 0)

        db_user.update_last_login(self.db_conn, user['musicbrainz_id'])
        user = db_user.get_by_mb_id(self.db_conn, user['musicbrainz_id'])

        # after update_last_login, the val should be greater than the old value i.e 0
        self.assertGreater(int(user['last_login'].strftime('%s')), 0)

    def test_update_user_details(self):
        user_id = db_user.create(self.db_conn, 17, "barbazfoo", "barbaz@foo.com")
        db_user.update_user_details(self.db_conn, user_id, "hello-world", "hello-world@foo.com")
        user = db_user.get(self.db_conn, user_id, fetch_email=True)
        self.assertEqual(user["id"], user_id)
        self.assertEqual(user["musicbrainz_id"], "hello-world")
        self.assertEqual(user["email"], "hello-world@foo.com")

    def test_get_all_users(self):
        """ Tests that get_all_users returns ALL users in the db """

        users = db_user.get_all_users(self.db_conn)
        self.assertEqual(len(users), 0)
        db_user.create(self.db_conn, 8, 'user1')
        users = db_user.get_all_users(self.db_conn)
        self.assertEqual(len(users), 1)
        db_user.create(self.db_conn, 9, 'user2')
        users = db_user.get_all_users(self.db_conn)
        self.assertEqual(len(users), 2)

    def test_get_all_users_columns(self):
        """ Tests that get_all_users only returns those columns which are asked for """

        # check that all columns of the user table are present
        # if columns is not specified
        users = db_user.get_all_users(self.db_conn)
        for user in users:
            for column in db_user.USER_GET_COLUMNS:
                self.assertIn(column, user)

        # check that only id is present if columns = ['id']
        users = db_user.get_all_users(self.db_conn, columns=['id'])
        for user in users:
            self.assertIn('id', user)
            for column in db_user.USER_GET_COLUMNS:
                if column != 'id':
                    self.assertNotIn(column, user)

    def test_delete(self):
        """Tests that deletes the given user"""

        user_id = db_user.create(self.db_conn, 10, 'frank')

        user = db_user.get(self.db_conn, user_id)
        self.assertIsNotNone(user)

        db_user.delete(self.db_conn, user_id)
        user = db_user.get(self.db_conn, user_id)
        self.assertIsNone(user)

    def test_pause(self):
        """ Tests that pauses the given user """

        user_id = db_user.create(self.db_conn, 39, 'anne')

        user = db_user.get(self.db_conn, user_id)
        self.assertEqual(user['is_paused'], False)

        db_user.pause(self.db_conn, user_id)
        user = db_user.get(self.db_conn, user_id)
        self.assertEqual(user['is_paused'], True)
        
    def test_unpause(self):
        """ Tests that pauses the given user """

        user_id = db_user.create(self.db_conn, 39, 'anne')

        user = db_user.get(self.db_conn, user_id)
        self.assertEqual(user['is_paused'], False)

        db_user.pause(self.db_conn, user_id)
        user = db_user.get(self.db_conn, user_id)
        self.assertEqual(user['is_paused'], True)

        db_user.unpause(self.db_conn, user_id)
        user = db_user.get(self.db_conn, user_id)
        self.assertEqual(user['is_paused'], False)

    def test_delete_when_spotify_import_activated(self):
        user_id = db_user.create(self.db_conn, 11, 'kishore')
        user = db_user.get(self.db_conn, user_id)
        self.assertIsNotNone(user)
        db_oauth.save_token(self.db_conn, user_id, ExternalServiceType.SPOTIFY, 'user token',
                            'refresh token', 0, True, ['user-read-recently-played'])

        db_user.delete(self.db_conn, user_id)
        user = db_user.get(self.db_conn, user_id)
        self.assertIsNone(user)
        token = db_oauth.get_token(self.db_conn, user_id, ExternalServiceType.SPOTIFY)
        self.assertIsNone(token)

    def test_get_similar_users(self):
        user_id_21 = db_user.create(self.db_conn, 21, "twenty_one")
        user_id_22 = db_user.create(self.db_conn, 22, "twenty_two")
        user_id_23 = db_user.create(self.db_conn, 23, "twenty_three")

        similar_users_21 = {str(user_id_22): 0.4, str(user_id_23): 0.7}
        similar_users_22 = {str(user_id_21): 0.4}
        similar_users_23 = {str(user_id_21): 0.7}

        similar_users = {
            str(user_id_21): similar_users_21,
            str(user_id_22): similar_users_22,
            str(user_id_23): similar_users_23,
        }

        import_user_similarities(similar_users)

        self.assertListEqual([
                {"id": user_id_23, "musicbrainz_id": "twenty_three", "similarity": 0.7},
                {"id": user_id_22, "musicbrainz_id": "twenty_two", "similarity": 0.4}
            ],
            db_user.get_similar_users(self.db_conn, user_id_21)
        )
        
        self.assertListEqual(
            [{"id": user_id_21, "musicbrainz_id": "twenty_one", "similarity": 0.4}],
            db_user.get_similar_users(self.db_conn, user_id_22)
        )
        
        self.assertListEqual(
            [{"id": user_id_21, "musicbrainz_id": "twenty_one", "similarity": 0.7}],
            db_user.get_similar_users(self.db_conn, user_id_23)
        )

    def test_get_user_by_id(self):
        user_id_24 = db_user.create(self.db_conn, 24, "twenty_four")
        user_id_25 = db_user.create(self.db_conn, 25, "twenty_five")

        users = {
            user_id_24: "twenty_four",
            user_id_25: "twenty_five"
        }

        self.assertDictEqual(users, db_user.get_users_by_id(self.db_conn, [user_id_24, user_id_25]))

    def test_fetch_email(self):
        musicbrainz_id = "one"
        email = "one@one.one"
        user_id = db_user.create(self.db_conn, 1, musicbrainz_id, email)
        self.assertNotIn("email", db_user.get(self.db_conn, user_id))
        self.assertEqual(email, db_user.get(self.db_conn, user_id, fetch_email=True)["email"])

        token = db_user.get(self.db_conn, user_id)["auth_token"]
        self.assertNotIn("email", db_user.get_by_token(self.db_conn, token))
        self.assertEqual(email, db_user.get_by_token(self.db_conn, token, fetch_email=True)["email"])

        self.assertNotIn("email", db_user.get_by_mb_id(self.db_conn, musicbrainz_id))
        self.assertEqual(email, db_user.get_by_mb_id(self.db_conn, musicbrainz_id, fetch_email=True)["email"])

    def test_search(self):
        searcher_id = db_user.create(self.db_conn, 0, "Cécile")
        user_id_c = db_user.create(self.db_conn, 1, "Cecile")
        user_id_l = db_user.create(self.db_conn, 2, "lucifer")
        user_id_r = db_user.create(self.db_conn, 3, "rob")

        self.db_conn.execute(sqlalchemy.text(
            "INSERT INTO recommendation.similar_user (user_id, similar_users) VALUES (:user_id, :similar_users)"),
            {
                "user_id": searcher_id,
                "similar_users": json.dumps({
                    str(user_id_c): 0.42,
                    str(user_id_l): 0.61,
                    str(user_id_r): 0.87
                })
            }
        )

        results = db_user.search(self.db_conn, "cif", 10, searcher_id)
        # changing this because the order of the list isnt being returned in a stable manner. 
        self.assertCountEqual(results, [("Cécile", 0.1, None), ("Cecile", 0.1, 0.42), ("lucifer", 0.09090909, 0.61)])

