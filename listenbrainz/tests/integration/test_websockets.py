import socketio
import json
import time
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase


class WebSocketTests(ListenAPIIntegrationTestCase):

    def setUp(self):
        super(WebSocketTests, self).setUp()
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.sio.connect("http://websockets:8102", wait_timeout=5)
        self.sio.emit("json", {"user": self.user["musicbrainz_id"]})

    def test_valid_single(self):
        """ Test for valid submission of listen_type listen """
        with open(self.path_to_data_file("valid_single.json"), "r") as f:
            payload = json.load(f)

        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        received_listen = None
        timeout = 5  # 5 seconds timeout

        @self.sio.event
        def listen(message):
            nonlocal received_listen
            received_listen = message

        start_time = time.time()
        while received_listen is None and time.time() - start_time < timeout:
            self.sio.sleep(1)
        self.assertIsNotNone(received_listen, "Did not receive the listen event within the timeout period.")

        received_listen = json.loads(received_listen)
        self.assertEqual(received_listen['track_metadata']['track_name'], 'Fade')
        self.assertEqual(received_listen['track_metadata']['artist_name'], 'Kanye West')
        self.assertEqual(received_listen['track_metadata']['release_name'], 'The Life of Pablo')
        self.assertEqual(received_listen['track_metadata']['additional_info']['music_service'], 'spotify.com')

    def test_valid_playing_now(self):
        """Test for valid submission of listen_type 'playing_now'"""

        with open(self.path_to_data_file("valid_playing_now.json"), "r") as f:
            payload = json.load(f)

        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        received_playing_now = None
        timeout = 5  # 5 seconds timeout

        @self.sio.event
        def playing_now(message):
            nonlocal received_playing_now
            received_playing_now = message

        # Wait for the 'playing_now' event
        start_time = time.time()
        while received_playing_now is None and time.time() - start_time < timeout:
            self.sio.sleep(1)

        self.assertIsNotNone(received_playing_now, "Did not receive the 'playing_now' event within the timeout period.")

        received_playing_now = json.loads(received_playing_now)
        self.assertEqual(received_playing_now['track_metadata']['track_name'], 'Fade')
        self.assertEqual(received_playing_now['track_metadata']['artist_name'], 'Kanye West')
        self.assertEqual(received_playing_now['track_metadata']['release_name'], 'The Life of Pablo')

        # Verify the data returned by the 'playing_now' endpoint
        r = self.client.get(self.custom_url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assert200(r)
        self.assertEqual(r.json['payload']['count'], 1)

    def tearDown(self):
        self.sio.disconnect()
        self.sio.wait()
