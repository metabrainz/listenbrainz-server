from unittest.mock import patch

from listenbrainz.tests.integration import IntegrationTestCase


class PlayerViewsTestCase(IntegrationTestCase):

    @patch("listenbrainz.webserver.views.player.fetch_playlist_recording_metadata")
    def test_player_get_instant(self, mock_recording_metadata):
        resp = self.client.get(
            self.custom_url_for('player.load_instant', recording_mbids="97e69767-5d34-4c97-b36a-f3b2b1ef9dae")
        )
        self.assert200(resp)

    @patch("listenbrainz.webserver.views.player.fetch_playlist_recording_metadata")
    def test_player_release(self, mock_recording_metadata):
        resp = self.client.get(
            self.custom_url_for('player.load_release', release_mbid="9db51cd6-38f6-3b42-8ad5-559963d68f35")
        )
        self.assert200(resp)
