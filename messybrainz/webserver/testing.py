import flask_testing
import os

from messybrainz.webserver import create_app


class ServerTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_app(config_path=os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..', 'test_config.py'
        ))
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            session['_fresh'] = True
