import json
import os
import time

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

    def wait_for_query_to_have_items(self, url, num_items, **kwargs):
        """Try the provided query in a loop until the required number of returned listens is available.
        In integration tests, we send data through a number of services before it hits the database,
        so we often have to wait. In some cases this takes longer than others, so we loop a few
        times until we have the correct number of items.

        Arguments:
            url: the url to GET
            num_items: The number of listens expected to be in the response
            kwargs: any additional arguments to pass to the client GET

        Returns the result from a flask client GET
        """
        count = 0
        while count < 5:
            count += 1
            time.sleep(2)

            response = self.client.get(url, **kwargs)
            data = json.loads(response.data)['payload']
            if data['count'] == num_items:
                break
        return response


class ListenAPIIntegrationTestCase(IntegrationTestCase, TimescaleTestCase):
    def setUp(self):
        IntegrationTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])
        self.user2 = db_user.get_or_create(2, 'all_muppets_all_of_them')

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
