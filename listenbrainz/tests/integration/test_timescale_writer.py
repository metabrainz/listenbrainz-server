
import sys
import os
import uuid
from random import randint

from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.listen import Listen
from listenbrainz.listenstore import TimescaleListenStore
from listenbrainz.listenstore import RedisListenStore
from flask import url_for
import listenbrainz.db.user as db_user
import time
import json

from listenbrainz import config
from datetime import datetime


class TimescaleWriterTestCase(IntegrationTestCase):

    def setUp(self):
        super(TimescaleWriterTestCase, self).setUp()
        self.ls = TimescaleListenStore({'REDIS_HOST': config.REDIS_HOST,
                                       'REDIS_PORT': config.REDIS_PORT,
                                       'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
                                       'SQLALCHEMY_TIMESCALE_URI': config.SQLALCHEMY_TIMESCALE_URI}, self.app.logger)
        self.rs = RedisListenStore(self.app.logger, { 'REDIS_HOST': config.REDIS_HOST,
                                   'REDIS_PORT': config.REDIS_PORT,
                                   'REDIS_NAMESPACE': config.REDIS_NAMESPACE})

    def tearDown(self):
        self.rs.redis.flushall()

    def send_listen(self, user, filename):
        with open(self.path_to_data_file(filename)) as f:
            payload = json.load(f)
        return self.client.post(
            url_for('api_v1.submit_listen'),
            data = json.dumps(payload),
            headers = {'Authorization': 'Token {}'.format(user['auth_token'])},
            content_type = 'application/json'
        )

    def test_dedup(self):

        user = db_user.get_or_create(1, 'testtimescaleuser %d' % randint(1,50000))

        # send the same listen twice
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)
        time.sleep(2)
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)
        time.sleep(2)

        to_ts = int(time.time())
        listens = self.ls.fetch_listens(user['musicbrainz_id'], to_ts=to_ts, time_range=-1)
        self.assertEqual(len(listens), 1)

        recent = self.rs.get_recent_listens(4)
        self.assertEqual(len(recent), 1)
        self.assertIsInstance(recent[0], Listen)

    def test_update_listen_count_per_day(self):
        """ Tests that timescale writer updates the listen count for the
        day in redis for each successful batch written
        """
        user = db_user.get_or_create(1, 'testtimescaleuser %d' % randint(1, 50000))
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)
        time.sleep(2)

        self.assertEqual(1, self.rs.get_listen_count_for_day(datetime.utcnow()))

    def test_dedup_user_special_characters(self):

        user = db_user.get_or_create(2, 'i have a\\weird\\user, name"\n')

        # send the same listen twice
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)
        time.sleep(2)
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)
        time.sleep(2)

        to_ts = int(time.time())
        listens = self.ls.fetch_listens(user['musicbrainz_id'], to_ts=to_ts, time_range=-1)
        self.assertEqual(len(listens), 1)


    def test_dedup_same_batch(self):

        user = db_user.get_or_create(3, 'phifedawg')
        r = self.send_listen(user, 'same_batch_duplicates.json')
        self.assert200(r)
        time.sleep(2)

        to_ts = int(time.time())
        listens = self.ls.fetch_listens(user['musicbrainz_id'], to_ts=to_ts, time_range=-1)
        self.assertEqual(len(listens), 1)


    def test_dedup_different_users(self):
        """
        Test to make sure timescale writer doesn't confuse listens with same timestamps
        but different users to be duplicates
        """

        user1 = db_user.get_or_create(1, 'testuser1')
        user2 = db_user.get_or_create(2, 'testuser2')

        r = self.send_listen(user1, 'valid_single.json')
        self.assert200(r)
        r = self.send_listen(user2, 'valid_single.json')
        self.assert200(r)

        time.sleep(2)  # sleep to allow timescale-writer to do its thing

        to_ts = int(time.time())
        listens = self.ls.fetch_listens(user1['musicbrainz_id'], to_ts=to_ts, time_range=-1)
        self.assertEqual(len(listens), 1)

        listens = self.ls.fetch_listens(user2['musicbrainz_id'], to_ts=to_ts, time_range=-1)
        self.assertEqual(len(listens), 1)


    def test_dedup_same_timestamp_different_tracks(self):
        """ Test to check that if there are two tracks w/ the same timestamp,
            they don't get considered as duplicates
        """

        user = db_user.get_or_create(1, 'difftracksametsuser')

        # send four different tracks with the same timestamp
        r = self.send_listen(user, 'valid_single.json')
        self.assert200(r)

        r = self.send_listen(user, 'same_timestamp_diff_track_valid_single.json')
        self.assert200(r)

        r = self.send_listen(user, 'same_timestamp_diff_track_valid_single_2.json')
        self.assert200(r)

        r = self.send_listen(user, 'same_timestamp_diff_track_valid_single_3.json')
        self.assert200(r)
        time.sleep(2)

        to_ts = int(time.time())
        listens = self.ls.fetch_listens(user['musicbrainz_id'], to_ts=to_ts, time_range=-1)
        self.assertEqual(len(listens), 4)
