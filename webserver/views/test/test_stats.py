from webserver.testing import ServerTestCase
from flask import url_for


class StatsViewsTestCase(ServerTestCase):

    def test_graph(self):
        resp = self.client.get(url_for('stats.graph'))
        self.assert200(resp)

    def test_data(self):
        resp = self.client.get(url_for('stats.data'))
        self.assert200(resp)
