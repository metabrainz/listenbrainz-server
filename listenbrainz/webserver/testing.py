import flask_testing
from listenbrainz.webserver import create_app, create_api_compat_app


class ServerTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_app()
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True


class APICompatServerTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_api_compat_app()
        app.config['TESTING'] = True
        return app
