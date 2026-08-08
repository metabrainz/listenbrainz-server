from unittest.mock import patch, MagicMock

from brainzutils.ratelimit import set_rate_limits

import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


class LBRadioAuthTest(IntegrationTestCase):

    def setUp(self):
        super().setUp()
        set_rate_limits(100000, 100000, 10)
        self.user = db_user.get_or_create(self.db_conn, 1, 'testuser_lb_radio')

    def _url(self):
        return self.custom_url_for('explore_api_v1.lb_radio', prompt='artist:(radiohead)', mode='easy')

    def _auth(self):
        return {"Authorization": f"Token {self.user['auth_token']}"}

    def test_unauthenticated_request_is_rejected(self):
        resp = self.client.get(self._url())
        self.assert401(resp)

    def test_invalid_token_is_rejected(self):
        resp = self.client.get(self._url(), headers={"Authorization": "Token notavalidtoken"})
        self.assert401(resp)

    @patch('listenbrainz.webserver.views.explore_api.LBRadioPatch')
    def test_valid_token_is_accepted(self, mock_patch_cls):
        mock_patch = MagicMock()
        mock_patch.generate_playlist.return_value = MagicMock(
            get_jspf=lambda: {"playlist": {"tracks": []}}
        )
        mock_patch.user_feedback.return_value = []
        mock_patch_cls.return_value = mock_patch

        resp = self.client.get(self._url(), headers=self._auth())
        self.assert200(resp)


class LBRadioRateLimitTest(IntegrationTestCase):
    """lb-radio has a separate, stricter rate limit than the global one."""

    def setUp(self):
        super().setUp()
        # Global limit is effectively unlimited so only the lb-radio limit fires.
        set_rate_limits(100000, 100000, 10)
        self.user = db_user.get_or_create(self.db_conn, 1, 'testuser_lb_radio_rl')

    def _url(self):
        return self.custom_url_for('explore_api_v1.lb_radio', prompt='artist:(radiohead)', mode='easy')

    def _auth(self):
        return {"Authorization": f"Token {self.user['auth_token']}"}

    @patch('listenbrainz.webserver.views.explore_api.LBRadioPatch')
    def test_requests_within_limit_succeed(self, mock_patch_cls):
        mock_patch = MagicMock()
        mock_patch.generate_playlist.return_value = MagicMock(
            get_jspf=lambda: {"playlist": {"tracks": []}}
        )
        mock_patch.user_feedback.return_value = []
        mock_patch_cls.return_value = mock_patch

        url, headers = self._url(), self._auth()
        for i in range(10):
            resp = self.client.get(url, headers=headers)
            self.assert200(resp, f"Request {i + 1} should succeed")

    @patch('listenbrainz.webserver.views.explore_api.LBRadioPatch')
    def test_request_over_limit_is_rejected(self, mock_patch_cls):
        mock_patch = MagicMock()
        mock_patch.generate_playlist.return_value = MagicMock(
            get_jspf=lambda: {"playlist": {"tracks": []}}
        )
        mock_patch.user_feedback.return_value = []
        mock_patch_cls.return_value = mock_patch

        url, headers = self._url(), self._auth()
        for _ in range(10):
            self.client.get(url, headers=headers)

        resp = self.client.get(url, headers=headers)
        self.assertEqual(resp.status_code, 429, "11th request should be rate-limited")
