from flask import url_for

from listenbrainz.tests.integration import IntegrationTestCase


class PlayerViewsTestCase(IntegrationTestCase):

    def test_player_get_instant(self):
        resp = self.client.get(url_for('player.load_instant', recording_mbids="97e69767-5d34-4c97-b36a-f3b2b1ef9dae"))
        self.assert200(resp)

    def test_player_release(self):
        resp = self.client.get(url_for('player.load_release', release_mbid="9db51cd6-38f6-3b42-8ad5-559963d68f35"))
        self.assert200(resp)
