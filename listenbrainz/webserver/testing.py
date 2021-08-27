import flask_testing

from listenbrainz.webserver import create_app, create_api_compat_app


class ServerTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_app(debug=False)
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_login_id):
        with self.client.session_transaction() as session:
            session['_user_id'] = user_login_id
            session['_fresh'] = True


class APICompatServerTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_api_compat_app()
        app.config['TESTING'] = True
        return app
