import json
import time

from unittest.mock import patch

from flask import url_for

from data.model.external_service import ExternalServiceType
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.listens_importer.spotify import SpotifyImporter
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.db import external_service_oauth


class SpotifyReaderTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super(SpotifyReaderTestCase, self).setUp()
        self.ctx = self.app.test_request_context()
        self.ctx.push()

        external_service_oauth.save_token(self.db_conn, user_id=self.user['id'],
                                          service=ExternalServiceType.SPOTIFY,
                                          access_token='token', refresh_token='refresh',
                                          token_expires_ts=int(time.time()) + 3000,
                                          record_listens=True,
                                          scopes=['user-read-recently-played'])

    def tearDown(self):
        self.ctx.pop()
        super(SpotifyReaderTestCase, self).tearDown()

    @patch.object(SpotifyImporter, 'get_user_currently_playing')
    @patch.object(SpotifyImporter, 'get_user_recently_played')
    def test_spotify_recently_played_submitted(self, mock_recently_played, mock_currently_playing):
        with open(self.path_to_data_file('spotify_recently_played_submitted.json')) as f:
            mock_recently_played.return_value = json.load(f)
        mock_currently_playing.return_value = None

        with self.app.app_context():
            importer = SpotifyImporter()
            result = importer.process_all_users()
            self.assertEqual(result, (1, 0))

        time.sleep(0.5)
        recalculate_all_user_data()

        with open(self.path_to_data_file('spotify_recently_played_expected.json')) as f:
            expected_data = json.load(f)

        url = url_for('api_v1.get_listens', user_name=self.user['musicbrainz_id'])
        r = self.wait_for_query_to_have_items(url, 1)
        self.assert200(r)

        payload = r.json['payload']
        self.assertEqual(payload['count'], 1)
        self.assertEqual(payload['latest_listen_ts'], 1635138793)

        actual_listen = payload['listens'][0]
        expected_listen = expected_data['payload']['listens'][0]
        # some fields vary from run to run, set those to our expected values before testing equality
        actual_listen['inserted_at'] = expected_listen['inserted_at']
        actual_listen['recording_msid'] = expected_listen['recording_msid']
        actual_listen['track_metadata']['additional_info']['recording_msid'] = \
            expected_listen['track_metadata']['additional_info']['recording_msid']

        self.assertEqual(expected_listen, actual_listen)
