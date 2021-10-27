from flask import url_for

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase


class HueSoundViewsTestCase(ServerTestCase, DatabaseTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def test_hue_sound(self):
        resp = self.client.get(url_for('color_api_v1.huesound', color="FF00FF"))
        self.assert200(resp)
