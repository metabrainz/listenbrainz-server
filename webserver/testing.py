import flask_testing
from db.testing import DatabaseTestCase
from webserver import create_app


class ServerTestCase(flask_testing.TestCase, DatabaseTestCase):

    def create_app(self):
        app = create_app()
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True
