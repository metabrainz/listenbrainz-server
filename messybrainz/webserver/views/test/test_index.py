from flask import url_for
from messybrainz.webserver import create_app
from messybrainz.webserver.testing import ServerTestCase


class IndexViewsTestCase(ServerTestCase):

    def test_home(self):
        resp = self.client.get(url_for('index.home'))
        self.assert200(resp)

    def test_flask_debugtoolbar(self):
        """ Test if flask debugtoolbar is loaded correctly

        Creating an app with default config so that debug is True
        and SECRET_KEY is defined.
        """
        app = create_app(debug=True)
        client = app.test_client()
        resp = client.get('/')
        self.assert200(resp)
        self.assertIn('flDebug', str(resp.data))
