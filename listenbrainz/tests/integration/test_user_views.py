import json

from flask import url_for

import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


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


