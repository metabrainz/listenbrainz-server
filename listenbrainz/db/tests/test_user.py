# -*- coding: utf-8 -*-
import time

import sqlalchemy

import listenbrainz.db.user as db_user
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

    def test_get_recently_logged_in_users(self):
        """Tests getting recently logged in users"""

        # create two users, set one's last_login
        # to a very old value and one's last_login
        # to now and then call get_recently_logged_in_users
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

        recent_users = db_user.get_recently_logged_in_users()
        self.assertEqual(len(recent_users), 1)
        self.assertEqual(recent_users[0]['musicbrainz_id'], 'recentuser2')

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

