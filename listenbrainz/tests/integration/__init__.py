import json
import os
import time

from flask import current_app, url_for, g

from redis import Redis

from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.webserver import ts_conn
from listenbrainz.webserver.testing import ServerTestCase, APICompatServerTestCase
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase

TIMESCALE_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'admin', 'timescale')


class IntegrationTestCase(ServerTestCase, DatabaseTestCase):

    @classmethod
    def setUpClass(cls):
        ServerTestCase.setUpClass()
        DatabaseTestCase.setUpClass()

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self._app_ctx = self.app.app_context()
        self._app_ctx.push()
        g.db_conn = self.conn

    def tearDown(self):
        self._app_ctx.pop()
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    @classmethod
    def tearDownClass(cls):
        ServerTestCase.tearDownClass()
        DatabaseTestCase.tearDownClass()


class ListenIntegrationTestCase(IntegrationTestCase, TimescaleTestCase):

    @classmethod
    def setUpClass(cls):
        IntegrationTestCase.setUpClass()
        TimescaleTestCase.setUpClass()

    def setUp(self):
        IntegrationTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        g.ts_conn = ts_conn

    def tearDown(self):
        IntegrationTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)


class ListenAPIIntegrationTestCase(IntegrationTestCase, TimescaleTestCase):

    @classmethod
    def setUpClass(cls):
        IntegrationTestCase.setUpClass()
        TimescaleTestCase.setUpClass()

    def setUp(self):
        IntegrationTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        g.ts_conn = self.ts_conn

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        IntegrationTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)

    @classmethod
    def tearDownClass(cls):
        IntegrationTestCase.tearDownClass()
        DatabaseTestCase.tearDownClass()

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
        while count < 10:
            count += 1
            time.sleep(1)

            response = self.client.get(url, **kwargs)
            data = json.loads(response.data)['payload']
            if data['count'] == num_items:
                break
        return response

    def send_data(self, payload, user, recalculate=False):
        """ Sends payload to api.submit_listen and return the response
        """
        response = self.client.post(
            url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            headers={'Authorization': 'Token {}'.format(user['auth_token'])},
            content_type='application/json'
        )
        if recalculate:
            # recalculate only if asked because there are many tests for invalid
            # submissions or where we don't fetch listens. in those cases, this
            # sleep will add unnecessary slowness.
            time.sleep(1)  # wait for listens to be picked up by timescale writer
            recalculate_all_user_data(self.conn, self.ts_conn)
        return response


class APICompatIntegrationTestCase(APICompatServerTestCase, DatabaseTestCase, TimescaleTestCase):

    @classmethod
    def setUpClass(cls):
        APICompatServerTestCase.setUpClass()
        DatabaseTestCase.setUpClass()
        TimescaleTestCase.setUpClass()

    @classmethod
    def tearDownClass(cls):
        APICompatServerTestCase.tearDownClass()
        DatabaseTestCase.tearDownClass()
        TimescaleTestCase.tearDownClass()

    def setUp(self):
        APICompatServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self._app_ctx = self.app.app_context()
        self._app_ctx.push()
        g.db_conn = self.conn
        g.ts_conn = self.ts_conn

    def tearDown(self):
        self._app_ctx.pop()
        APICompatServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)
