
from listenbrainz.webserver.testing import ServerTestCase
from flask import url_for
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
import time
import ujson

class UserViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create('iliekcomputers')

    def test_user_page(self):
        response = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(response)

    def test_latest_import(self):
        """ Test for user.latest_import """

        # initially the value of latest_import will be 0
        response = self.client.get(url_for('user.latest_import'), query_string={'user_name': self.user['musicbrainz_id']})
        self.assert200(response)
        data = ujson.loads(response.data)
        self.assertEqual(data['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(data['latest_import'], 0)

        # now an update
        val = int(time.time())
        response = self.client.post(
            url_for('user.latest_import'),
            data=ujson.dumps({'ts': val}),
            headers={'Authorization': 'Token {token}'.format(token=self.user['auth_token'])}
        )
        self.assert200(response)

        # now the value must have changed
        response = self.client.get(url_for('user.latest_import'), query_string={'user_name': self.user['musicbrainz_id']})
        self.assert200(response)
        data = ujson.loads(response.data)
        self.assertEqual(data['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(data['latest_import'], val)

    def test_latest_import_unauthorized(self):
        """ Test for invalid tokens passed to user.latest_import view"""

        val = int(time.time())
        response = self.client.post(
            url_for('user.latest_import'),
            data=ujson.dumps({'ts': val}),
            headers={'Authorization': 'Token thisisinvalid'}
        )
        self.assert401(response)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)
