from __future__ import print_function
import flask_testing
from webserver import create_web_app, create_api_app, create_single_app
from werkzeug.wsgi import DispatcherMiddleware


class WebAppTestCase(flask_testing.TestCase):
    """ Class to inherit from for testing the WebApp. """
    def create_app(self):
        app = create_web_app()
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True


class APITestCase(flask_testing.TestCase):
    """ Class to inherit from for testing the API Flask app. """
    def create_app(self):
        app = create_api_app()
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True


class ServerTestCase(flask_testing.TestCase):
    """ Class to inherit from for integration tests involving both Flask apps. """

    def create_app(self):
        app = create_single_app()
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True
