
from listenbrainz.webserver.testing import ServerTestCase
from flask import url_for
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase

class UserViewsTestCase(ServerTestCase, DatabaseTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create('iliekcomputers')

    def test_user_page(self):
        response = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(response)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)
