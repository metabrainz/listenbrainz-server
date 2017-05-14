from __future__ import absolute_import, print_function
import sys
import os
import uuid
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))

from tests.integration import IntegrationTestCase
from listenstore import InfluxListenStore
from flask import url_for
import db.user
import time
import json
import config
from influxdb import InfluxDBClient

class InfluxWriterTestCase(IntegrationTestCase):

    def setUp(self):
        super(InfluxWriterTestCase, self).setUp()
        self.ls = InfluxListenStore({ 'REDIS_HOST' : config.REDIS_HOST,
                             'REDIS_PORT' : config.REDIS_PORT,
                             'INFLUX_HOST': config.INFLUX_HOST,
                             'INFLUX_PORT': config.INFLUX_PORT,
                             'INFLUX_DB_NAME': config.INFLUX_DB_NAME})

    def send_single_listen(self, user):
        with open(self.path_to_data_file('valid_single.json')) as f:
            payload = json.load(f)
        return self.client.post(
            url_for('api_v1.submit_listen'),
            data = json.dumps(payload),
            headers = {'Authorization': 'Token {}'.format(user['auth_token'])},
            content_type = 'application/json'
        )

    def test_dedup(self):

        user = db.user.get_or_create('testinfluxwriteruser')

        # send the same listen twice
        r = self.send_single_listen(user)
        self.assert200(r)
        time.sleep(5)
        r = self.send_single_listen(user)
        self.assert200(r)
        time.sleep(5)

        to_ts = int(time.time())
        listens = self.ls.fetch_listens(user['musicbrainz_id'], to_ts=to_ts)
        self.assertEqual(len(listens), 1)

    def test_dedup_different_users(self):
        """
        Test to make sure influx writer doesn't confuse listens with same timestamps
        but different users to be duplicates
        """

        user1 = db.user.get_or_create('testuser1')
        user2 = db.user.get_or_create('testuser2')

        r = self.send_single_listen(user1)
        r = self.send_single_listen(user2)

        time.sleep(5) # sleep to allow influx-writer to do its thing

        to_ts = int(time.time())
        listens = self.ls.fetch_listens(user1['musicbrainz_id'], to_ts=to_ts)
        self.assertEqual(len(listens), 1)

        listens = self.ls.fetch_listens(user2['musicbrainz_id'], to_ts=to_ts)
        self.assertEqual(len(listens), 1)
