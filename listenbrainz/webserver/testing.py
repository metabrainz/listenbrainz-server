import flask_testing

from listenbrainz.webserver import create_api_compat_app, create_web_app


class ServerTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_web_app(debug=False)
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_login_id):
        with self.client.session_transaction() as session:
            session['_user_id'] = user_login_id
            session['_fresh'] = True

    def assertRedirects(self, response, location, message=None, permanent=False):
        if permanent:
            valid_status_codes = (301, 308)
        else:
            valid_status_codes = (301, 302, 303, 305, 307, 308)

        valid_status_code_str = ', '.join(str(code) for code in valid_status_codes)
        not_redirect = "HTTP Status %s expected but got %d" % (valid_status_code_str, response.status_code)

        self.assertIn(response.status_code, valid_status_codes, message or not_redirect)
        self.assertTrue(response.location.endswith(location), message)

    assert_redirects = assertRedirects


class APICompatServerTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_api_compat_app()
        app.config['TESTING'] = True
        return app
