
from listenbrainz.webserver.testing import ServerTestCase
from flask import url_for


class IndexViewsTestCase(ServerTestCase):

    def test_index(self):
        resp = self.client.get(url_for('index.index'))
        self.assert200(resp)

    def test_downloads(self):
        resp = self.client.get(url_for('index.downloads'))
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
