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
        
        data = json.loads(response.data)['payload']

        # make sure user id is correct
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

        # make sure that count is 1 and list also contains 1 listen
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['listens']), 1)

        # make sure timestamp is the same as sent
        sent_time = payload['payload'][0]['listened_at']
        self.assertEqual(data['listens'][0]['listened_at'], sent_time)
        self.assertEqual(data['listens'][0]
                         ['track_metadata']['track_name'], 'Fade')
        self.assertEqual(data['listens'][0]['track_metadata']
                         ['artist_name'], 'Kanye West')
        self.assertEqual(data['listens'][0]['track_metadata']
                         ['release_name'], 'The Life of Pablo')
        self.assertEqual(data['listens'][0]['track_metadata']
                         ['additional_info']['music_service'], 'spotify.com')

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
        self.assertEqual(len(r.json['payload']['listens']), 1)
        self.assertEqual(r.json['payload']['user_id'],
                         self.user['musicbrainz_id'])
        self.assertEqual(r.json['payload']['listens'][0]
                         ['track_metadata']['artist_name'], 'Kanye West')
        self.assertEqual(r.json['payload']['listens'][0]
                         ['track_metadata']['release_name'], 'The Life of Pablo')
        self.assertEqual(r.json['payload']['listens'][0]
                         ['track_metadata']['track_name'], 'Fade')

    def tearDown(self):
        self.sio.disconnect()
        self.sio.wait()