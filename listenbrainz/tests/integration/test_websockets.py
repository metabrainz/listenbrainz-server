import socketio
import json
import time
import requests
import pytest
from flask import url_for
from unittest.mock import patch
import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
from data.model.external_service import ExternalServiceType
from listenbrainz import db
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver.views.api_tools import is_valid_uuid
import listenbrainz.db.external_service_oauth as db_oauth

class WebSocketTests(ListenAPIIntegrationTestCase):
    def setUp(self):
        super(WebSocketTests, self).setUp()
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.sio.connect('http://websockets:8102', wait_timeout=20)
        self.sio.wait()
        self.listen_received = None
        self.sio.on('listen', self.on_listen)

    def test_valid_single(self):
        """ Test for valid submission of listen_type listen """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        received_listen = False
        timeout = 20  # 20 seconds timeout

        @self.sio.event
        def connect():
            print('Connected to the WebSockets server')

        @self.sio.event
        def listen(data):
            nonlocal received_listen
            print('Received listen event:', data)
            received_listen = True

        try:
            self.sio.connect('http://websockets:8102')
            start_time = time.time()
            while not received_listen and time.time() - start_time < timeout:
                self.sio.sleep(0.1)
            self.assertTrue(received_listen, 'Did not receive the listen event within the timeout period.')
        finally:
            self.sio.disconnect()

    def on_listen(self, data):
        """Callback function for the 'listen' event"""
        self.listen_received = data
        print(f"Received listen: {data}")

    def tearDown(self):
        self.sio.disconnect()