# -*- coding: utf-8 -*-
from db.testing import DatabaseTestCase
import db.user


class UserTestCase(DatabaseTestCase):

    def test_create(self):
        user_id = db.user.create("izzy_cheezy")
        self.assertIsNotNone(db.user.get(user_id))

    def test_update_token(self):
        user = db.user.get_or_create('testuserplsignore')
        old_token = user['auth_token']
        db.user.update_token(user['id'])
        user = db.user.get_by_mb_id('testuserplsignore')
        self.assertNotEqual(old_token, user['auth_token'])
