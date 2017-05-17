from __future__ import absolute_import
from webserver.testing import WebAppTestCase
from flask import url_for
import db
from db.testing import DatabaseTestCase

class UserViewsTestCase(WebAppTestCase, DatabaseTestCase):

    def setUp(self):
        WebAppTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db.user.get_or_create('iliekcomputers')

    def test_user_page(self):
        response = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(response)

    def tearDown(self):
        WebAppTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)
