# -*- coding: utf-8 -*-
from listenbrainz.db.testing import DatabaseTestCase
import listenbrainz.db.user as db_user
from listenbrainz import db
import time
import sqlalchemy


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
        user = db_user.get_or_create('testlatestimportuser')

        val = int(time.time())
        db_user.update_latest_import(user['musicbrainz_id'], val)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(val, int(user['latest_import'].strftime('%s')))

        db_user.update_latest_import(user['musicbrainz_id'], val - 10)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(val, int(user['latest_import'].strftime('%s')))

        val += 10
        db_user.update_latest_import(user['musicbrainz_id'], val)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(val, int(user['latest_import'].strftime('%s')))
