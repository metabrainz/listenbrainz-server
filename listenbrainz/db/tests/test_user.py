# -*- coding: utf-8 -*-

import listenbrainz.db.user as db_user
import listenbrainz.db.external_service_oauth as db_oauth
import listenbrainz.db.stats as db_stats
import sqlalchemy
import time
import ujson

from data.model.external_service import ExternalServiceType
from listenbrainz import db
from listenbrainz.db.similar_users import import_user_similarities
from listenbrainz.db.testing import DatabaseTestCase
from data.model.user_artist_stat import UserArtistStatJson


class UserTestCase(DatabaseTestCase):
    def test_create(self):
        user_id = db_user.create(0, "izzy_cheezy")
        self.assertIsNotNone(db_user.get(user_id))

    def test_get_by_musicbrainz_row_id(self):
        user_id = db_user.create(0, 'frank')
        user = db_user.get_by_mb_row_id(0)
        self.assertEqual(user['id'], user_id)
        user = db_user.get_by_mb_row_id(0, musicbrainz_id='frank')
        self.assertEqual(user['id'], user_id)

    def test_update_token(self):
        user = db_user.get_or_create(1, 'testuserplsignore')
        old_token = user['auth_token']
        db_user.update_token(user['id'])
        user = db_user.get_by_mb_id('testuserplsignore')
        self.assertNotEqual(old_token, user['auth_token'])

    def test_update_last_login(self):
        """ Tests db.user.update_last_login """

        user = db_user.get_or_create(2, 'testlastloginuser')

        # set the last login value of the user to 0
        with db.engine.connect() as connection:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET last_login = to_timestamp(0)
                 WHERE id = :id
            """), {
                'id': user['id']
            })

        user = db_user.get(user['id'])
        self.assertEqual(int(user['last_login'].strftime('%s')), 0)

        db_user.update_last_login(user['musicbrainz_id'])
        user = db_user.get_by_mb_id(user['musicbrainz_id'])

        # after update_last_login, the val should be greater than the old value i.e 0
        self.assertGreater(int(user['last_login'].strftime('%s')), 0)

    def test_get_all_users(self):
        """ Tests that get_all_users returns ALL users in the db """

        users = db_user.get_all_users()
        self.assertEqual(len(users), 0)
        db_user.create(8, 'user1')
        users = db_user.get_all_users()
        self.assertEqual(len(users), 1)
        db_user.create(9, 'user2')
        users = db_user.get_all_users()
        self.assertEqual(len(users), 2)

    def test_get_all_users_columns(self):
        """ Tests that get_all_users only returns those columns which are asked for """

        # check that all columns of the user table are present
        # if columns is not specified
        users = db_user.get_all_users()
        for user in users:
            for column in db_user.USER_GET_COLUMNS:
                self.assertIn(column, user)

        # check that only id is present if columns = ['id']
        users = db_user.get_all_users(columns=['id'])
        for user in users:
            self.assertIn('id', user)
            for column in db_user.USER_GET_COLUMNS:
                if column != 'id':
                    self.assertNotIn(column, user)

    def test_delete(self):
        user_id = db_user.create(10, 'frank')

        user = db_user.get(user_id)
        self.assertIsNotNone(user)

        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = ujson.load(f)
        db_stats.insert_user_artists(
            user_id=user_id,
            artists=UserArtistStatJson(**{'all_time': artists_data}),
        )
        user_stats = db_stats.get_user_artists(user_id, 'all_time')
        self.assertIsNotNone(user_stats)

        db_user.delete(user_id)
        user = db_user.get(user_id)
        self.assertIsNone(user)
        user_stats = db_stats.get_user_artists(user_id, 'all_time')
        self.assertIsNone(user_stats)

    def test_delete_when_spotify_import_activated(self):
        user_id = db_user.create(11, 'kishore')
        user = db_user.get(user_id)
        self.assertIsNotNone(user)
        db_oauth.save_token(user_id, ExternalServiceType.SPOTIFY, 'user token',
                            'refresh token', 0, True, ['user-read-recently-played'])

        db_user.delete(user_id)
        user = db_user.get(user_id)
        self.assertIsNone(user)
        token = db_oauth.get_token(user_id, ExternalServiceType.SPOTIFY)
        self.assertIsNone(token)

    def test_validate_usernames(self):
        db_user.create(11, 'eleven')
        db_user.create(12, 'twelve')

        users = db_user.validate_usernames([])
        self.assertListEqual(users, [])

        users = db_user.validate_usernames(['eleven', 'twelve'])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['musicbrainz_id'], 'eleven')
        self.assertEqual(users[1]['musicbrainz_id'], 'twelve')

        users = db_user.validate_usernames(['twelve', 'eleven'])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['musicbrainz_id'], 'twelve')
        self.assertEqual(users[1]['musicbrainz_id'], 'eleven')

        users = db_user.validate_usernames(['twelve', 'eleven', 'thirteen'])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['musicbrainz_id'], 'twelve')
        self.assertEqual(users[1]['musicbrainz_id'], 'eleven')

    def test_get_users_in_order(self):
        id1 = db_user.create(11, 'eleven')
        id2 = db_user.create(12, 'twelve')

        users = db_user.get_users_in_order([])
        self.assertListEqual(users, [])

        users = db_user.get_users_in_order([id1, id2])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['id'], id1)
        self.assertEqual(users[1]['id'], id2)

        users = db_user.get_users_in_order([id2, id1])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['id'], id2)
        self.assertEqual(users[1]['id'], id1)

        users = db_user.get_users_in_order([id2, id1, 213213132])
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['id'], id2)
        self.assertEqual(users[1]['id'], id1)

    def test_get_similar_users(self):
        user_id_21 = db_user.create(21, "twenty_one")
        user_id_22 = db_user.create(22, "twenty_two")
        user_id_23 = db_user.create(23, "twenty_three")

        similar_users_21 = {"twenty_two": [0.4, .01], "twenty_three": [0.7, 0.001]}
        similar_users_22 = {"twenty_one": [0.4, .01]}
        similar_users_23 = {"twenty_one": [0.7, .02]}

        similar_users = {
            "twenty_one": similar_users_21,
            "twenty_two": similar_users_22,
            "twenty_three": similar_users_23,
        }

        import_user_similarities(similar_users)

        self.assertDictEqual({"twenty_two": 0.4, "twenty_three": 0.7},
                             db_user.get_similar_users(user_id_21).similar_users)
        self.assertDictEqual({"twenty_one": 0.4 },
                             db_user.get_similar_users(user_id_22).similar_users)
        self.assertDictEqual({"twenty_one": 0.7},
                             db_user.get_similar_users(user_id_23).similar_users)

    def test_get_user_by_id(self):
        user_id_24 = db_user.create(24, "twenty_four")
        user_id_25 = db_user.create(25, "twenty_five")

        users = {
            user_id_24: "twenty_four",
            user_id_25: "twenty_five"
        }

        self.assertDictEqual(users, db_user.get_users_by_id([user_id_24, user_id_25]))

    def test_fetch_email(self):
        musicbrainz_id = "one"
        email = "one@one.one"
        user_id = db_user.create(1, musicbrainz_id, email)
        self.assertNotIn("email", db_user.get(user_id))
        self.assertEqual(email, db_user.get(user_id, fetch_email=True)["email"])

        token = db_user.get(user_id)["auth_token"]
        self.assertNotIn("email", db_user.get_by_token(token))
        self.assertEqual(email, db_user.get_by_token(token, fetch_email=True)["email"])

        self.assertNotIn("email", db_user.get_by_mb_id(musicbrainz_id))
        self.assertEqual(email, db_user.get_by_mb_id(musicbrainz_id, fetch_email=True)["email"])
