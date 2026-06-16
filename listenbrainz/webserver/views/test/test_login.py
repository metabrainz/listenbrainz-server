from urllib.parse import parse_qs, urlparse

from listenbrainz.webserver.testing import ServerTestCase


class LoginViewsTestCase(ServerTestCase):

    def test_login_musicbrainz_redirects(self):
        response = self.client.get(self.custom_url_for('login.musicbrainz'))
        self.assertStatus(response, 302)

    def test_login_musicbrainz_forwards_register_hint_to_oauth_domain(self):
        response = self.client.get(
            self.custom_url_for('login.musicbrainz', login_hint='register')
        )
        self.assertStatus(response, 302)

        parsed_url = urlparse(response.location)
        parsed_authorize_url = urlparse(self.app.config["OAUTH_AUTHORIZE_URL"])
        query = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.scheme, parsed_authorize_url.scheme)
        self.assertEqual(parsed_url.netloc, parsed_authorize_url.netloc)
        self.assertEqual(parsed_url.path, parsed_authorize_url.path)
        self.assertEqual(query["login_hint"], ["register"])

    def test_login_musicbrainz_does_not_forward_unknown_login_hint(self):
        response = self.client.get(
            self.custom_url_for('login.musicbrainz', login_hint='invalid')
        )
        self.assertStatus(response, 302)

        query = parse_qs(urlparse(response.location).query)
        self.assertNotIn("login_hint", query)
