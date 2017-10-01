
import sys
import os
import uuid
from listenbrainz.tests.integration import IntegrationTestCase
from flask import url_for
import listenbrainz.db.user as db_user
import time
import json

class UserViewsTestCase(IntegrationTestCase):

    def setUp(self):
        super(UserViewsTestCase, self).setUp()
        self.user = db_user.get_or_create('iliekcomputers')

    def send_listens(self):
        with open(self.path_to_data_file('user_export_test.json')) as f:
            payload = json.load(f)
        return self.client.post(
            url_for('api_v1.submit_listen'),
            data = json.dumps(payload),
            headers = {'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type = 'application/json'
        )

    def test_export(self):
        """
        Test for the user export of ListenBrainz data.
        """
        # test get requests to export view first
        self.temporary_login(self.user['id'])
        resp = self.client.get(url_for('user.export_data'))
        self.assert200(resp)

        # send two listens for the user
        resp = self.send_listens()
        self.assert200(resp)

        time.sleep(2)

        # now export data and check if contains all the listens we just sent
        resp = self.client.post(url_for('user.export_data'))
        self.assert200(resp)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 3)
