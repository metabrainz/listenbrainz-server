
from listenbrainz.webserver.testing import ServerTestCase


class LoginViewsTestCase(ServerTestCase):

    def test_login_page(self):
        response = self.client.get(self.custom_url_for('login.index'))
        self.assert200(response)
