
from listenbrainz.webserver.testing import ServerTestCase


class LoginViewsTestCase(ServerTestCase):

    def test_login_musicbrainz_redirects(self):
        response = self.client.get(self.custom_url_for('login.musicbrainz'))
        self.assertStatus(response, 302)
