from __future__ import print_function
import flask_testing
from webserver import create_web_app, create_api_app, create_app
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
        from webserver.webapp.views.index import index_bp
        from webserver.webapp.views.login import login_bp
        from webserver.webapp.views.user import user_bp
        from webserver.api.views.api import api_bp
        from webserver.api.views.api_compat import api_bp as api_bp_compat
        blueprints = [
            (index_bp, ''),
            (login_bp, '/login'),
            (user_bp, '/user'),
            (api_bp, ''),
            (api_bp_compat, ''),
        ]
        print("Creating an app in ServerTestCase")
        app = create_app(blueprints)
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True
