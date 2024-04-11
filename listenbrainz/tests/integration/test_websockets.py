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
            self.assertEqual(data['listen_type'], payload['listen_type'])
            self.assertEqual(data['payload'][0]['listened_at'], payload['payload'][0]['listened_at'])
            self.assertEqual(data['payload'][0]['track_metadata']['artist_name'], payload['payload'][0]['track_metadata']['artist_name'])
            self.assertEqual(data['payload'][0]['track_metadata']['track_name'], payload['payload'][0]['track_metadata']['track_name'])
            self.assertEqual(data['payload'][0]['track_metadata']['release_name'], payload['payload'][0]['track_metadata']['release_name'])
            self.assertEqual(data['payload'][0]['track_metadata']['additional_info']['music_service'], payload['payload'][0]['track_metadata']['additional_info']['music_service'])
            self.assertEqual(data['payload'][0]['track_metadata']['additional_info']['recording_msid'], payload['payload'][0]['track_metadata']['additional_info']['recording_msid'])
            received_listen = True

        start_time = time.time()
        while not received_listen and time.time() - start_time < timeout:
            self.sio.sleep(1)
        self.assertTrue(received_listen, "Did not receive the listen event within the timeout period.")

    def test_valid_playing_now(self):
        """Test for valid submission of listen_type 'playing_now'"""
        with open(self.path_to_data_file('valid_playing_now.json'), 'r') as f:
            payload = json.load(f)

        # Send the data using WebSockets
        received_playing_now = False
        timeout = 20  # 20 seconds timeout

        @self.sio.event
        def playing_now(data):
            nonlocal received_playing_now
            self.assertEqual(data, payload)
            received_playing_now = True

        start_time = time.time()
        self.sio.emit('playing_now', payload)

        while not received_playing_now and time.time() - start_time < timeout:
            self.sio.sleep(1)

        self.assertTrue(received_playing_now, "Did not receive the 'playing_now' event within the timeout period.")

        # Check the API response
        r = self.client.get(self.custom_url_for('api_v1.get_playing_now',
                                            user_name=self.user['musicbrainz_id']))
        self.assert200(r)
        self.assertEqual(r.json['payload']['count'], 1)

    def tearDown(self):
        self.sio.disconnect()
        self.sio.wait()
