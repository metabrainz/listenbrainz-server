
import listenbrainz.db.user as db_user
import logging
from datetime import datetime
from sqlalchemy import text


from listenbrainz import config as config
from listenbrainz import db
from listenbrainz.db.lastfm_user import User
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.tests.utils import generate_data
from listenbrainz.webserver.influx_connection import init_influx_connection


class TestAPICompatUserClass(DatabaseTestCase):

    def setUp(self):
        super(TestAPICompatUserClass, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = init_influx_connection(self.log, {
            'INFLUX_HOST': config.INFLUX_HOST,
            'INFLUX_PORT': config.INFLUX_PORT,
            'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
            'REDIS_HOST': config.REDIS_HOST,
            'REDIS_PORT': config.REDIS_PORT,
            'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
        })

        # Create a user
        uid = db_user.create("test_api_compat_user")
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
        test_data = generate_data(date, 100, self.user.name)
        self.assertEqual(len(test_data), 100)
        self.logstore.insert(test_data)
        count = User.get_play_count(self.user.id, self.logstore)
        self.assertEqual(count, 100)
