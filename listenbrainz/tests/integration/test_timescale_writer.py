import json
import time
from datetime import datetime, timezone
from random import randint

import listenbrainz.db.user as db_user
from listenbrainz.listen import Listen
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import NonAPIIntegrationTestCase
from listenbrainz.webserver import redis_connection, timescale_connection


class TimescaleWriterTestCase(NonAPIIntegrationTestCase):

    def setUp(self):
        super(TimescaleWriterTestCase, self).setUp()
        self.ls = timescale_connection._ts
        self.rs = redis_connection._redis

    def send_listen(self, user, filename):
        with open(self.path_to_data_file(filename)) as f:
            payload = json.load(f)
        response = self.client.post(
            self.custom_url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            headers={'Authorization': 'Token {}'.format(user['auth_token'])},
            content_type='application/json'
        )
        time.sleep(1)  # sleep to allow timescale-writer to do its thing
        recalculate_all_user_data()
        return response

    def test_dedup(self):
        user = db_user.get_or_create(self.db_conn, 1, 'testtimescaleuser %d' % randint(1,50000))

        # send the same listen twice
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)

        to_ts = datetime.now(timezone.utc)
        listens, _, _ = self.ls.fetch_listens(user, to_ts=to_ts)
        self.assertEqual(len(listens), 1)

        recent = self.rs.get_recent_listens(4)
        print(recent)
        self.assertEqual(len(recent), 1)
        self.assertIsInstance(recent[0], Listen)

    def test_update_listen_count_per_day_and_test_timestamps(self):
        """ Tests that timescale writer updates the listen count for the
        day in redis for each successful batch written and to see if the user
        timestamps via the timescale listen store are updated in redis.
        """
        user = db_user.get_or_create(self.db_conn, 1, 'testtimescaleuser %d' % randint(1, 50000))
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)

        self.assertEqual(1, self.rs.get_listen_count_for_day(datetime.now(timezone.utc)))

        (min_ts, max_ts) = self.ls.get_timestamps_for_user(user["id"])
        self.assertEqual(min_ts, datetime.fromtimestamp(1486449409, timezone.utc))
        self.assertEqual(max_ts, datetime.fromtimestamp(1486449409, timezone.utc))

    def test_dedup_user_special_characters(self):

        user = db_user.get_or_create(self.db_conn, 2, 'i have a\\weird\\user, name"\n')

        # send the same listen twice
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)
        to_ts = datetime.now(timezone.utc)
        listens, _, _ = self.ls.fetch_listens(user, to_ts=to_ts)
        self.assertEqual(len(listens), 1)

    def test_dedup_same_batch(self):

        user = db_user.get_or_create(self.db_conn, 3, 'phifedawg')
        r = self.send_listen(user, 'same_batch_duplicates.json')
        self.assert200(r)

        to_ts = datetime.now(timezone.utc)
        listens, _, _ = self.ls.fetch_listens(user, to_ts=to_ts)
        self.assertEqual(len(listens), 1)

    def test_dedup_different_users(self):
        """
        Test to make sure timescale writer doesn't confuse listens with same timestamps
        but different users to be duplicates
        """

        user1 = db_user.get_or_create(self.db_conn, 1, 'testuser1')
        user2 = db_user.get_or_create(self.db_conn, 2, 'testuser2')

        r = self.send_listen(user1, 'valid_single.json')
        self.assert200(r)
        r = self.send_listen(user2, 'valid_single.json')
        self.assert200(r)

        to_ts = datetime.now(timezone.utc)
        listens, _, _ = self.ls.fetch_listens(user1, to_ts=to_ts)
        self.assertEqual(len(listens), 1)

        listens, _, _ = self.ls.fetch_listens(user2, to_ts=to_ts)
        self.assertEqual(len(listens), 1)

    def test_dedup_same_timestamp_different_tracks(self):
        """ Test to check that if there are two tracks w/ the same timestamp,
            they don't get considered as duplicates
        """

        user = db_user.get_or_create(self.db_conn, 1, 'difftracksametsuser')

        # send four different tracks with the same timestamp
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)

        r = self.send_listen(user, 'same_timestamp_diff_track_valid_single.json')
        self.assert200(r)

        r = self.send_listen(user, 'same_timestamp_diff_track_valid_single_2.json')
        self.assert200(r)

        r = self.send_listen(user, 'same_timestamp_diff_track_valid_single_3.json')
        self.assert200(r)

        to_ts = datetime.now(timezone.utc)
        listens, _, _ = self.ls.fetch_listens(user, to_ts=to_ts)
        self.assertEqual(len(listens), 4)
