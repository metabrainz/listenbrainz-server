# -*- coding: utf-8 -*-
from listenbrainz.db.testing import DatabaseTestCase
import listenbrainz.db.user as db_user
import time


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
        user = db_user.get_or_create('testlastloginuser')
        val = int(time.time())
        db_user.update_last_login(user['musicbrainz_id'], val)
        user = db_user.get_by_mb_id(user['musicbrainz_id'])
        self.assertEqual(val, int(user['last_login'].strftime('%s')))
