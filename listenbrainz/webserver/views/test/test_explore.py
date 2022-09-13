import datetime
from unittest.mock import patch

from flask import url_for

from listenbrainz.tests.integration import IntegrationTestCase


class ExploreViewsTestCase(IntegrationTestCase):

    def test_hue_sound(self):
        resp = self.client.get(url_for('explore.huesound', color="FF00FF"))
        self.assert200(resp)

    def test_hue_sound_redirect(self):
        resp = self.client.get(url_for('index.huesound', color="FF00FF"))
        self.assertStatus(resp, 302)

    def test_similar_users(self):
        resp = self.client.get(url_for('explore.similar_users'))
        self.assert200(resp)

    def test_similar_users_redirect(self):
        resp = self.client.get(url_for('index.similar_users'))
        self.assertStatus(resp, 302)

    def test_fresh_releases(self):
        resp = self.client.get(url_for('explore.fresh_releases'))
        self.assert200(resp)

    @patch('listenbrainz.db.fresh_releases.get_sitewide_fresh_releases')
    def test_fresh_releases_api(self, mock_fresh):
        resp = self.client.get(url_for('explore_api_v1.get_fresh_releases'))
        self.assert200(resp)
        mock_fresh.assert_called_with(datetime.date.today(), 14)

        resp = self.client.get(url_for('explore_api_v1.get_fresh_releases', release_date="2022-01-01", days=5))
        self.assert200(resp)
        mock_fresh.assert_called_with(datetime.date(year=2022, month=1, day=1), 5)
