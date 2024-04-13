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
        
        received_listen = False
        timeout = 5  # 5 seconds timeout

        @self.sio.event
        def listen(data):
            nonlocal received_listen
            received_listen = True

        start_time = time.time()
        while not received_listen and time.time() - start_time < timeout:
            self.sio.sleep(1)
        self.assertTrue(received_listen, "Did not receive the listen event within the timeout period.")

    def test_valid_playing_now(self):
        """Test for valid submission of listen_type 'playing_now'"""

        with open(self.path_to_data_file("valid_playing_now.json"), "r") as f:
            payload = json.load(f)

        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        received_playing_now = False
        timeout = 5  # 20 seconds timeout

        @self.sio.event
        def playing_now(data):
            nonlocal received_playing_now
            received_playing_now = True

        # Wait for the 'playing_now' event
        start_time = time.time()
        while not received_playing_now and time.time() - start_time < timeout:
            self.sio.sleep(1)

        self.assertTrue(received_playing_now, "Did not receive the 'playing_now' event within the timeout period.")

        # Verify the data returned by the 'playing_now' endpoint
        r = self.client.get(self.custom_url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assert200(r)
        self.assertEqual(r.json['payload']['count'], 1)

    def tearDown(self):
        self.sio.disconnect()
        self.sio.wait()