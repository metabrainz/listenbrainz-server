# -*- coding: utf-8 -*-
import json

import listenbrainz.db.user as db_user
import listenbrainz.db.external_service_oauth as db_oauth
import listenbrainz.db.stats as db_stats
import sqlalchemy
import ujson

from data.model.common_stat import StatRange
from data.model.external_service import ExternalServiceType
from data.model.user_entity import EntityRecord
from listenbrainz.db.testing import DatabaseTestCase


class UserTestCase(DatabaseTestCase):
    def test_create(self):
        user_id = db_user.create(self.conn, 0, "izzy_cheezy")
        self.assertIsNotNone(db_user.get(self.conn, user_id))

    def test_get_by_musicbrainz_row_id(self):
        user_id = db_user.create(self.conn, 0, 'frank')
        user = db_user.get_by_mb_row_id(self.conn, 0)
        self.assertEqual(user['id'], user_id)
        user = db_user.get_by_mb_row_id(self.conn, 0, musicbrainz_id='frank')
        self.assertEqual(user['id'], user_id)

    def test_update_token(self):
        user = db_user.get_or_create(self.conn, 1, 'testuserplsignore')
        old_token = user['auth_token']
        db_user.update_token(user['id'])
        user = db_user.get_by_mb_id(self.conn, 'testuserplsignore')
        self.assertNotEqual(old_token, user['auth_token'])

    def test_update_last_login(self):
        """ Tests db.user.update_last_login """

        user = db_user.get_or_create(self.conn, 2, 'testlastloginuser')

        # set the last login value of the user to 0
        self.conn.execute(sqlalchemy.text("""
            UPDATE "user"
               SET last_login = to_timestamp(0)
             WHERE id = :id
        """), {
            'id': user['id']
        })

        user = db_user.get(self.conn, user['id'])
        self.assertEqual(int(user['last_login'].strftime('%s')), 0)

        db_user.update_last_login(self.conn, user['musicbrainz_id'])
        user = db_user.get_by_mb_id(self.conn, user['musicbrainz_id'])

        # after update_last_login, the val should be greater than the old value i.e 0
        self.assertGreater(int(user['last_login'].strftime('%s')), 0)

    def test_update_user_details(self):
        user_id = db_user.create(self.conn, 17, "barbazfoo", "barbaz@foo.com")
        db_user.update_user_details(self.conn, user_id, "hello-world", "hello-world@foo.com")
        user = db_user.get(self.conn, user_id, fetch_email=True)
        self.assertEqual(user["id"], user_id)
        self.assertEqual(user["musicbrainz_id"], "hello-world")
        self.assertEqual(user["email"], "hello-world@foo.com")

    def test_get_all_users(self):
        """ Tests that get_all_users returns ALL users in the db """

        users = db_user.get_all_users(self.conn)
        self.assertEqual(len(users), 0)
        db_user.create(self.conn, 8, 'user1')
        users = db_user.get_all_users(self.conn)
        self.assertEqual(len(users), 1)
        db_user.create(self.conn, 9, 'user2')
        users = db_user.get_all_users(self.conn)
        self.assertEqual(len(users), 2)

    def test_get_all_users_columns(self):
        """ Tests that get_all_users only returns those columns which are asked for """

        # check that all columns of the user table are present
        # if columns is not specified
        users = db_user.get_all_users(self.conn)
        for user in users:
            for column in db_user.USER_GET_COLUMNS:
                self.assertIn(column, user)

        # check that only id is present if columns = ['id']
        users = db_user.get_all_users(self.conn, columns=['id'])
        for user in users:
            self.assertIn('id', user)
            for column in db_user.USER_GET_COLUMNS:
                if column != 'id':
                    self.assertNotIn(column, user)

    def test_delete(self):
        user_id = db_user.create(self.conn, 10, 'frank')

        user = db_user.get(self.conn, user_id)
        self.assertIsNotNone(user)

        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = ujson.load(f)
        db_stats.insert_user_jsonb_data(
            user_id=user_id,
            stats_type='artists',
            stats=StatRange[EntityRecord](**artists_data),
        )
        user_stats = db_stats.get_user_stats(user_id, 'all_time', 'artists')
        self.assertIsNotNone(user_stats)

        db_user.delete(self.conn, user_id)
        user = db_user.get(self.conn, user_id)
        self.assertIsNone(user)
        user_stats = db_stats.get_user_stats(user_id, 'all_time', 'artists')
        self.assertIsNone(user_stats)

    def test_delete_when_spotify_import_activated(self):
        user_id = db_user.create(self.conn, 11, 'kishore')
        user = db_user.get(self.conn, user_id)
        self.assertIsNotNone(user)
        db_oauth.save_token(user_id, ExternalServiceType.SPOTIFY, 'user token',
                            'refresh token', 0, True, ['user-read-recently-played'])

        db_user.delete(self.conn, user_id)
        user = db_user.get(self.conn, user_id)
        self.assertIsNone(user)
        token = db_oauth.get_token(user_id, ExternalServiceType.SPOTIFY)
        self.assertIsNone(token)

    def test_validate_usernames(self):
        db_user.create(self.conn, 11, 'eleven')
        db_user.create(self.conn, 12, 'twelve')

        users = db_user.validate_usernames(self.conn, [])
        self.assertListEqual(users, [])

        users = db_user.validate_usernames(self.conn, ['eleven', 'twelve'])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['musicbrainz_id'], 'eleven')
        self.assertEqual(users[1]['musicbrainz_id'], 'twelve')

        users = db_user.validate_usernames(self.conn, ['twelve', 'eleven'])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['musicbrainz_id'], 'twelve')
        self.assertEqual(users[1]['musicbrainz_id'], 'eleven')

        users = db_user.validate_usernames(self.conn, ['twelve', 'eleven', 'thirteen'])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['musicbrainz_id'], 'twelve')
        self.assertEqual(users[1]['musicbrainz_id'], 'eleven')

    def test_get_users_in_order(self):
        id1 = db_user.create(self.conn, 11, 'eleven')
        id2 = db_user.create(self.conn, 12, 'twelve')

        users = db_user.get_users_in_order(self.conn, [])
        self.assertListEqual(users, [])

        users = db_user.get_users_in_order(self.conn, [id1, id2])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['id'], id1)
        self.assertEqual(users[1]['id'], id2)

        users = db_user.get_users_in_order(self.conn, [id2, id1])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['id'], id2)
        self.assertEqual(users[1]['id'], id1)

        users = db_user.get_users_in_order(self.conn, [id2, id1, 213213132])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['id'], id2)
        self.assertEqual(users[1]['id'], id1)

    def test_get_similar_users(self):
        user_id_21 = db_user.create(self.conn, 21, "twenty_one")
        user_id_22 = db_user.create(self.conn, 22, "twenty_two")
        user_id_23 = db_user.create(self.conn, 23, "twenty_three")

        similar_users_21 = {str(user_id_22): [0.4, .01], str(user_id_23): [0.7, 0.001]}
        similar_users_22 = {str(user_id_21): [0.4, .01]}
        similar_users_23 = {str(user_id_21): [0.7, .02]}

        query = sqlalchemy.text("INSERT INTO recommendation.similar_user (user_id, similar_users)"
                                "     VALUES (:user_id, :similar_users)")
        self.conn.execute(query, user_id=user_id_21, similar_users=json.dumps(similar_users_21))
        self.conn.execute(query, user_id=user_id_22, similar_users=json.dumps(similar_users_22))
        self.conn.execute(query, user_id=user_id_23, similar_users=json.dumps(similar_users_23))

        self.assertDictEqual({"twenty_two": 0.4, "twenty_three": 0.7},
                             db_user.get_similar_users(user_id_21).similar_users)
        self.assertDictEqual({"twenty_one": 0.4},
                             db_user.get_similar_users(user_id_22).similar_users)
        self.assertDictEqual({"twenty_one": 0.7},
                             db_user.get_similar_users(user_id_23).similar_users)

    def test_get_user_by_id(self):
        user_id_24 = db_user.create(self.conn, 24, "twenty_four")
        user_id_25 = db_user.create(self.conn, 25, "twenty_five")

        users = {
            user_id_24: "twenty_four",
            user_id_25: "twenty_five"
        }

        self.assertDictEqual(users, db_user.get_users_by_id(self.conn, [user_id_24, user_id_25]))

    def test_fetch_email(self):
        musicbrainz_id = "one"
        email = "one@one.one"
        user_id = db_user.create(self.conn, 1, musicbrainz_id, email)
        self.assertNotIn("email", db_user.get(self.conn, user_id))
        self.assertEqual(email, db_user.get(self.conn, user_id, fetch_email=True)["email"])

        token = db_user.get(self.conn, user_id)["auth_token"]
        self.assertNotIn("email", db_user.get_by_token(self.conn, token))
        self.assertEqual(email, db_user.get_by_token(self.conn, token, fetch_email=True)["email"])

        self.assertNotIn("email", db_user.get_by_mb_id(self.conn, musicbrainz_id))
        self.assertEqual(email, db_user.get_by_mb_id(self.conn, musicbrainz_id, fetch_email=True)["email"])

    def test_search(self):
        searcher_id = db_user.create(self.conn, 0, "Cécile")
        user_id_c = db_user.create(self.conn, 1, "Cecile")
        user_id_l = db_user.create(self.conn, 2, "lucifer")
        user_id_r = db_user.create(self.conn, 3, "rob")

        self.conn.execute(sqlalchemy.text(
            "INSERT INTO recommendation.similar_user (user_id, similar_users) VALUES (:user_id, :similar_users)"),
            user_id=searcher_id,
            similar_users=json.dumps({
                str(user_id_c): [0.42, 0.20],
                str(user_id_l): [0.61, 0.25],
                str(user_id_r): [0.87, 0.43]
            })
        )

        results = db_user.search(self.conn, "cif", 10, searcher_id)
        self.assertEqual(results, [("Cécile", 0.1, None), ("Cecile", 0.1, 0.42), ("lucifer", 0.0909091, 0.61)])
