import json
import sys
import os
import listenbrainz.db.user as db_user
from flask import current_app, url_for

from redis import Redis
from listenbrainz import config
from listenbrainz.webserver.testing import ServerTestCase, APICompatServerTestCase
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import timescale as ts

TIMESCALE_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'admin', 'timescale')


class IntegrationTestCase(ServerTestCase, DatabaseTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

class ListenAPIIntegrationTestCase(IntegrationTestCase):
    def setUp(self):
        super(ListenAPIIntegrationTestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        self.reset_timescale_db()
        super(ListenAPIIntegrationTestCase, self).tearDown()

    def reset_timescale_db(self):

        ts.init_db_connection(config.TIMESCALE_ADMIN_URI)
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'drop_db.sql'))
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_db.sql'))
        ts.engine.dispose()

        ts.init_db_connection(config.TIMESCALE_ADMIN_LB_URI)
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_extensions.sql'))
        ts.engine.dispose()

        ts.init_db_connection(config.SQLALCHEMY_TIMESCALE_URI)
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_tables.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_functions.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_views.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_indexes.sql'))
        ts.engine.dispose()

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
