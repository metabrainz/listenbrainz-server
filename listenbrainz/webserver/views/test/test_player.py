import requests_mock
from flask import url_for

from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver.views.playlist_api import RECORDING_LOOKUP_SERVER_URL


class PlayerViewsTestCase(IntegrationTestCase):

    @requests_mock.Mocker()
    def test_instant_playlist(self, mock_requests):
        mock_requests.post(RECORDING_LOOKUP_SERVER_URL, status_code=200, json=[
            {
                "[artist_credit_mbids]": [
                    "e8f70e00-d9fb-4e2a-847f-7d6f3b9db965"
                ],
                "artist_credit_id": 2819203,
                "artist_credit_name" : "Repairs",
                "comment": "",
                "length": 100000,
                "original_recording_mbid": "878f6802-a8c0-4c1a-af2e-e5af1ccd5412",
                "recording_mbid": "0f53fa2f-f015-40c6-a5cd-f17af596764c",
                "recording_name":"Thanks for the Advice"
            }
        ])
        resp = self.client.get(url_for('player.load_instant', recording_mbids="878f6802-a8c0-4c1a-af2e-e5af1ccd5412"))
        self.assert200(resp)

    def test_player_release(self):
        resp = self.client.get(url_for('player.load_release', release_mbid="9db51cd6-38f6-3b42-8ad5-559963d68f35"))
        self.assert200(resp)
