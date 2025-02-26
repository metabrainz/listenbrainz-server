
import logging
import uuid
from datetime import datetime, time

import listenbrainz.db.user as db_user
from listenbrainz.db.lastfm_user import User
from listenbrainz.listen import Listen
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import timescale_connection


class TestAPICompatUserClass(IntegrationTestCase):

    def setUp(self):
        super(TestAPICompatUserClass, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = timescale_connection._ts

        # Create a user
        uid = db_user.create(self.db_conn, 1009, "test_api_compat_user")
        user_dict = db_user.get(self.db_conn, uid)
        self.user = User(user_dict["id"], user_dict["created"], user_dict["musicbrainz_id"], user_dict["auth_token"])

    def test_user_get_id(self):
        uid = User.get_id(self.db_conn, self.user.name)
        self.assertEqual(uid, self.user.id)

    def test_user_load_by_name(self):
        user = User.load_by_name(self.db_conn, self.user.name)
        self.assertTrue(isinstance(user, User))
        self.assertDictEqual(user.__dict__, self.user.__dict__)

    def test_user_load_by_id(self):
        user = User.load_by_id(self.db_conn, self.user.id)
        self.assertTrue(isinstance(user, User))
        self.assertDictEqual(user.__dict__, self.user.__dict__)

    def generate_data(self, from_date, num_records):
        test_data = []
        current_date = int(from_date.timestamp())

        for i in range(num_records):
            current_date += 1  # Add one second
            item = Listen(
                user_id=self.user.id,
                user_name=self.user.name,
                timestamp=current_date,
                recording_msid=str(uuid.uuid4()),
                data={
                    'artist_name': 'Test Artist Pls ignore',
                    'track_name': 'Hello Goodbye',
                    'additional_info': {},
                },
            )
            test_data.append(item)
        return test_data

    def test_user_get_play_count(self):
        date = datetime(2015, 9, 3, 0, 0, 0)
        test_data = self.generate_data(date, 5)
        self.assertEqual(len(test_data), 5)
        self.logstore.insert(test_data)
        with self.app.app_context():
            count = User.get_play_count(self.db_conn, self.user.id, self.logstore)
            self.assertIsInstance(count, int)
