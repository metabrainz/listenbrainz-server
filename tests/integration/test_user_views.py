from __future__ import absolute_import, print_function
import sys
import os
import uuid
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))

from tests.integration import IntegrationTestCase
from flask import url_for
import db.user
import time
import json

TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'testdata')

class UserViewsTestCase(IntegrationTestCase):

    def setUp(self):
        super(UserViewsTestCase, self).setUp()
        self.user = db.user.get_or_create('testuserpleaseignore')

    def send_listens(self):
        with open(self.path_to_data_file('valid_import.json')) as f:
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

        time.sleep(5)

        # now export data and check if contains all the listens we just sent
        resp = self.client.post(url_for('user.export_data'))
        self.assert200(resp)
        data = json.loads(resp.data)
        self.assertEquals(len(data), 2)

    def path_to_data_file(self, fn):
        """ Returns the path of the test data file relative to the test file.

            Args:
                fn: the name of the data file
        """
        return os.path.join(TEST_DATA_PATH, fn)
