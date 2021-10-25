from flask import url_for
from unittest import mock
from unittest.mock import MagicMock

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase


class HueSoundViewsTestCase(ServerTestCase, DatabaseTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

#    @mock.patch('listenbrainz.db.color.get_releases_for_color')
#        mock_colors.return_value = []
#   def test_hue_sound(self, mock_colors):
    def test_hue_sound(self):
        resp = self.client.get(url_for('color_api_v1.huesound', color="FF00FF"))
        self.assert200(resp)
