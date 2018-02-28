from flask import url_for
from listenbrainz.webserver import create_app
from listenbrainz.webserver.testing import ServerTestCase


class IndexViewsTestCase(ServerTestCase):

    def test_index(self):
        resp = self.client.get(url_for('index.index'))
        self.assert200(resp)

    def test_downloads(self):
        resp = self.client.get(url_for('index.downloads'))
        self.assert_redirects(resp, url_for('index.data'))

    def test_data(self):
        resp = self.client.get(url_for('index.data'))
        self.assert200(resp)

    def test_contribute(self):
        resp = self.client.get(url_for('index.contribute'))
        self.assert200(resp)

    def test_goals(self):
        resp = self.client.get(url_for('index.goals'))
        self.assert200(resp)

    def test_faq(self):
        resp = self.client.get(url_for('index.faq'))
        self.assert200(resp)

    def test_api_docs(self):
        resp = self.client.get(url_for('index.api_docs'))
        self.assert200(resp)

    def test_roadmap(self):
        resp = self.client.get(url_for('index.roadmap'))
        self.assert200(resp)

    def test_404(self):
        resp = self.client.get('/canyoufindthis')
        self.assert404(resp)
        self.assertIn('Not Found', resp.data.decode('utf-8'))

    def test_lastfm_proxy(self):
        resp = self.client.get(url_for('index.proxy'))
        self.assert200(resp)

    def test_flask_debugtoolbar(self):
        """ Test if flask debugtoolbar is loaded correctly

        Creating an app with default config so that debug is True
        and SECRET_KEY is defined.
        """
        app = create_app(debug=True)
        client = app.test_client()
        resp = client.get('/data')
        self.assert200(resp)
        self.assertIn('flDebug', str(resp.data))

    def test_current_status(self):
        resp = self.client.get(url_for('index.current_status'))
        self.assert200(resp)
