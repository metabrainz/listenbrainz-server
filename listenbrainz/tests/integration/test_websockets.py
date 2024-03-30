import socketio
import json
import time
import requests
from unittest.mock import patch

import pytest
from flask import url_for

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
        self.sio.connect('http://localhost:8102',wait_timeout = 20)
        self.http_session = requests.Session()
        print(self.sio)

    def test_get_listens(self):
        """ Test to verify that the WebSocket server receives listens submitted via the API """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)
        # Send a listen
        print(payload)
        ts = int(time.time())
        payload['payload'][0]['listened_at'] = ts
        response = self.send_data(payload)
        print(response)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

    def send_data(self, payload, user):
        if not user:
            user = self.user
        response = self.http_session.post(
            self.custom_url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            # headers={'Authorization': 'Token {}'.format(user['auth_token'])},
            headers={'content-type': 'application/json'}
        )
        return response
    
    def tearDown(self):
        # Close the HTTP session after the test
        self.http_session.close()