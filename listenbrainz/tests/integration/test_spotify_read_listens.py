import json
import time

from flask import url_for
from unittest.mock import patch

from data.model.external_service import ExternalServiceType
from listenbrainz.spotify_updater import spotify_read_listens
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.db import external_service_oauth

class SpotifyReaderTestCase(ListenAPIIntegrationTestCase):
    def setUp(self):
        super(SpotifyReaderTestCase, self).setUp()
        external_service_oauth.save_token(user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                                          access_token='token', refresh_token='refresh',
                                          token_expires_ts=int(time.time()) + 3000, record_listens=True,
                                          scopes=['user-read-recently-played'])

    @patch('listenbrainz.spotify_updater.spotify_read_listens.get_user_currently_playing')
    @patch('listenbrainz.spotify_updater.spotify_read_listens.get_user_recently_played')
    def test_spotify_recently_played_submitted(self, mock_recently_played, mock_currently_playing):
        with open(self.path_to_data_file('spotify_recently_played_submitted.json')) as f:
            mock_recently_played.return_value = json.load(f)
        mock_currently_playing.return_value = None

        result = spotify_read_listens.process_all_spotify_users()
        self.assertEqual(result, (1, 0))

        with open(self.path_to_data_file('spotify_recently_played_expected.json')) as f:
            expected_listens = json.load(f)

        url = url_for('api_v1.get_listens', user_name=self.user['musicbrainz_id'])
        r = self.wait_for_query_to_have_items(url, 1)
        self.assert200(r)
        self.assertEqual(expected_listens, r.json)