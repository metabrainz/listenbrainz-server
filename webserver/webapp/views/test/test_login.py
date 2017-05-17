from __future__ import absolute_import
from webserver.testing import WebAppTestCase
from flask import url_for


class LoginViewsTestCase(WebAppTestCase):

    def test_login_page(self):
        response = self.client.get(url_for('login.index'))
        self.assert200(response)
