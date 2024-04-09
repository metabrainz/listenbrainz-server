import socketio
import json
import time

from listenbrainz.tests.integration import ListenAPIIntegrationTestCase


class WebSocketTests(ListenAPIIntegrationTestCase):

    def setUp(self):
        super(WebSocketTests, self).setUp()
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.sio.connect("http://websockets:8102", wait_timeout=5)

    def test_valid_single(self):
        """ Test for valid submission of listen_type listen """
        with open(self.path_to_data_file("valid_single.json"), "r") as f:
            payload = json.load(f)

        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        received_listen = False
        timeout = 20  # 20 seconds timeout

        @self.sio.event
        def listen(data):
            nonlocal received_listen
            received_listen = True

        start_time = time.time()
        while not received_listen and time.time() - start_time < timeout:
            self.sio.sleep(1)
        self.assertTrue(received_listen, "Did not receive the listen event within the timeout period.")

    def tearDown(self):
        self.sio.disconnect()
        self.sio.wait()
