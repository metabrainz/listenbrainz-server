import json
import os
import listenbrainz.db.user as db_user
from flask import current_app, url_for

from redis import Redis
from listenbrainz.webserver.testing import ServerTestCase, APICompatServerTestCase
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase

TIMESCALE_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'admin', 'timescale')


class IntegrationTestCase(ServerTestCase, DatabaseTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)


class ListenAPIIntegrationTestCase(IntegrationTestCase, TimescaleTestCase):
    def setUp(self):
        IntegrationTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        IntegrationTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)

    def send_data(self, payload, user=None):
        """ Sends payload to api.submit_listen and return the response
        """
        if not user:
            user = self.user
        return self.client.post(
            url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            headers={'Authorization': 'Token {}'.format(user['auth_token'])},
            content_type='application/json'
        )


class APICompatIntegrationTestCase(APICompatServerTestCase, DatabaseTestCase):

    def setUp(self):
        APICompatServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        APICompatServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)
