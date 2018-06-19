# -*- coding: utf-8 -*-

import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats
import sqlalchemy
import time
import ujson

from listenbrainz import db
from listenbrainz.db.testing import DatabaseTestCase


class UserTestCase(DatabaseTestCase):

    def test_create(self):
        user_id = db_user.create("izzy_cheezy")
        self.assertIsNotNone(db_user.get(user_id))

    def test_update_token(self):
        user = db_user.get_or_create('testuserplsignore')
        old_token = user['auth_token']
        db_user.update_token(user['id'])
        user = db_user.get_by_mb_id('testuserplsignore')
        self.assertNotEqual(old_token, user['auth_token'])

    def test_update_last_login(self):
        """ Tests db.user.update_last_login """

        user = db_user.get_or_create('testlastloginuser')

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
        self.assertEquals(int(user['last_login'].strftime('%s')), 0)

        db_user.update_last_login(user['musicbrainz_id'])
        user = db_user.get_by_mb_id(user['musicbrainz_id'])

        # after update_last_login, the val should be greater than the old value i.e 0
        self.assertGreater(int(user['last_login'].strftime('%s')), 0)

    def test_update_latest_import(self):
        user = db_user.get_or_create('updatelatestimportuser')
        self.assertEqual(int(user['latest_import'].strftime('%s')), 0)

        val = int(time.time())
        db_user.update_latest_import(user['musicbrainz_id'], val)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(int(user['latest_import'].strftime('%s')), val)

    def test_increase_latest_import(self):
        user = db_user.get_or_create('testlatestimportuser')

        val = int(time.time())
        db_user.increase_latest_import(user['musicbrainz_id'], val)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(val, int(user['latest_import'].strftime('%s')))

        db_user.increase_latest_import(user['musicbrainz_id'], val - 10)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(val, int(user['latest_import'].strftime('%s')))

        val += 10
        db_user.increase_latest_import(user['musicbrainz_id'], val)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(val, int(user['latest_import'].strftime('%s')))

    def test_get_users_with_uncalculated_stats(self):

        # create two users, set one's last_login
        # to a very old value and one's last_login
        # to now and then call the function
        user1 = db_user.get_or_create('recentuser1')
        with db.engine.connect() as connection:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET last_login = to_timestamp(0)
                 WHERE musicbrainz_id = :musicbrainz_id
                """), {
                    'musicbrainz_id': 'recentuser1'
                })

        user2 = db_user.get_or_create('recentuser2')
        with db.engine.connect() as connection:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET last_login = NOW()
                 WHERE musicbrainz_id = :musicbrainz_id
                """), {
                    'musicbrainz_id': 'recentuser2'
                })

        users_with_uncalculated_stats = db_user.get_users_with_uncalculated_stats()
        self.assertEqual(len(users_with_uncalculated_stats), 1)
        self.assertEqual(users_with_uncalculated_stats[0]['musicbrainz_id'], 'recentuser2')


        # now if we've calculated the stats for user2 recently (just now)
        # then the function shouldn't return user2

        # put some data in the stats table for user2
        with db.engine.connect() as connection:
            connection.execute(sqlalchemy.text("""
                INSERT INTO statistics.user (user_id, artist, release, recording, last_updated)
                     VALUES (:user_id, :artist, :release, :recording, NOW())
            """), {
                'user_id': user2['id'],
                'artist': ujson.dumps({}),
                'release': ujson.dumps({}),
                'recording': ujson.dumps({}),
            })

        users_with_uncalculated_stats = db_user.get_users_with_uncalculated_stats()
        self.assertListEqual(users_with_uncalculated_stats, [])

    def test_reset_latest_import(self):
        user = db_user.get_or_create('resetlatestimportuser')
        self.assertEqual(int(user['latest_import'].strftime('%s')), 0)

        val = int(time.time())
        db_user.update_latest_import(user['musicbrainz_id'], val)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(int(user['latest_import'].strftime('%s')), val)

        db_user.reset_latest_import(user['musicbrainz_id'])
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(int(user['latest_import'].strftime('%s')), 0)

    def test_get_all_users(self):
        """ Tests that get_all_users returns ALL users in the db """

        users = db_user.get_all_users()
        self.assertEqual(len(users), 0)
        db_user.create('user1')
        users = db_user.get_all_users()
        self.assertEqual(len(users), 1)
        db_user.create('user2')
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
        users = db_user.get_all_users(['id'])
        for user in users:
            self.assertIn('id', user)
            for column in db_user.USER_GET_COLUMNS:
                if column != 'id':
                    self.assertNotIn(column, user)

    def test_delete(self):
        user_id = db_user.create('frank')

        user = db_user.get(user_id)
        self.assertIsNotNone(user)
        db_stats.insert_user_stats(
            user_id=user_id,
            artists={},
            recordings={},
            releases={},
            artist_count=2,
        )
        user_stats = db_stats.get_all_user_stats(user_id)
        self.assertIsNotNone(user_stats)

        db_user.delete(user_id)
        user = db_user.get(user_id)
        self.assertIsNone(user)
        user_stats = db_stats.get_all_user_stats(user_id)
        self.assertIsNone(user_stats)
