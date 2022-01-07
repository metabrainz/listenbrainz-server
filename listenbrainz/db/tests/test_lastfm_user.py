
import logging
from datetime import datetime

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz import db
from listenbrainz.db.lastfm_user import User
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.tests.utils import generate_data
from listenbrainz.webserver import timescale_connection


class TestAPICompatUserClass(DatabaseTestCase):

    def setUp(self):
        super(TestAPICompatUserClass, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = timescale_connection._ts

        # Create a user
        uid = db_user.create(1, "test_api_compat_user")
        self.assertIsNotNone(db_user.get(uid))
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT *
                  FROM "user"
                 WHERE id = :id
            """), {
                "id": uid,
            })
            row = result.fetchone()
            self.user = User(row['id'], row['created'], row['musicbrainz_id'], row['auth_token'])

    def tearDown(self):
        super(TestAPICompatUserClass, self).tearDown()

    def test_user_get_id(self):
        uid = User.get_id(self.user.name)
        self.assertEqual(uid, self.user.id)

    def test_user_load_by_name(self):
        user = User.load_by_name(self.user.name)
        self.assertTrue(isinstance(user, User))
        self.assertDictEqual(user.__dict__, self.user.__dict__)

    def test_user_load_by_id(self):
        user = User.load_by_id(self.user.id)
        self.assertTrue(isinstance(user, User))
        self.assertDictEqual(user.__dict__, self.user.__dict__)

    def test_user_get_play_count(self):
        date = datetime(2015, 9, 3, 0, 0, 0)
        test_data = generate_data(date, 5, self.user.name)
        self.assertEqual(len(test_data), 5)
        self.logstore.insert(test_data)
        count = User.get_play_count(self.user.id, self.logstore)
        self.assertIsInstance(count, int)
