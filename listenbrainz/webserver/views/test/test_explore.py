import datetime
from unittest import mock
from unittest.mock import patch

from listenbrainz.tests.integration import IntegrationTestCase


class ExploreViewsTestCase(IntegrationTestCase):

    def test_hue_sound(self):
        resp = self.client.get(self.custom_url_for('explore.index', path="huesound"))
        self.assert200(resp)

    def test_similar_users(self):
        resp = self.client.get(self.custom_url_for('explore.index', path="similar-users"))
        self.assert200(resp)

    def test_fresh_releases(self):
        resp = self.client.get(self.custom_url_for('explore.index', path="fresh-releases"))
        self.assert200(resp)

    @patch('listenbrainz.db.fresh_releases.get_sitewide_fresh_releases', side_effect=[([], 0), ([], 0), ([], 0)])
    def test_fresh_releases_api(self, mock_fresh):
        resp = self.client.get(self.custom_url_for('explore_api_v1.get_fresh_releases'))
        self.assert200(resp)
        mock_fresh.assert_called_with(mock.ANY, datetime.date.today(), 14, 'release_date', True, True)

        resp = self.client.get(self.custom_url_for('explore_api_v1.get_fresh_releases', release_date="2022-01-01", days=5))
        self.assert200(resp)
        mock_fresh.assert_called_with(mock.ANY, datetime.date(year=2022, month=1, day=1), 5, 'release_date', True, True)

        resp = self.client.get(self.custom_url_for('explore_api_v1.get_fresh_releases', sort="artist_credit_name", past=False))
        self.assert200(resp)
        mock_fresh.assert_called_with(mock.ANY, datetime.date.today(), 14, 'artist_credit_name', False, True)

    def test_lb_radio(self):
        resp = self.client.get(self.custom_url_for('explore.index', path="lb-radio"))
        self.assert200(resp)
