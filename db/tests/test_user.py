# -*- coding: utf-8 -*-
from db.testing import DatabaseTestCase
import db.user


class UserTestCase(DatabaseTestCase):

    def test_create(self):
        user_id = db.user.create("izzy_cheezy")
        self.assertIsNotNone(db.user.get(user_id))
