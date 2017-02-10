from __future__ import absolute_import
from webserver.testing import ServerTestCase
from flask import url_for
import db.user
import time
import json
import os

class APITestCase(ServerTestCase):

    def setUp(self):
        self.user = db.user.get_or_create('testuserpleaseignore')

    def test_get_listens(self):
        """ Test to see that get_listens returns valid response
        """
        payload = {
            'max_ts': str(int(time.time())),
            'count': '25'
        }
        url = url_for('api_v1.get_listens', user_name = self.user['musicbrainz_id'])
        response = self.client.get(url, query_string=payload)
        self.assert200(response)

    def send_data(self, payload):
        """ Sends payload to api.submit_listen and return the response
        """
        return self.client.post(
            url_for('api_v1.submit_listen'),
            data = json.dumps(payload),
            headers = {'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type = 'application/json'
        )

    def test_unauthorized_submission(self):
        """ Test for checking that unauthorized submissions return 401
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'valid_single.json'), 'r') as f:
            payload = json.load(f)

        # request with no authorization header
        response = self.client.post(
            url_for('api_v1.submit_listen'),
            data = json.dumps(payload),
            content_type = 'application/json'
        )
        self.assert401(response)

        # request with invalid authorization header
        response = self.client.post(
            url_for('api_v1.submit_listen'),
            data = json.dumps(payload),
            headers = {'Authorization' : 'Token testtokenplsignore'},
            content_type = 'application/json'
        )
        self.assert401(response)

    def test_valid_single(self):
        """ Test for valid submissioon of listen_type listen
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'valid_single.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)

    def test_single_more_than_one_listen(self):
        """ Test for an invalid submission which has listen_type 'single' but
            more thean one listen in payload
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'single_more_than_one_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_valid_playing_now(self):
        """ Test for valid submission of listen_type 'playing_now'
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'valid_playing_now.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)

    def test_playing_now_with_ts(self):
        """ Test for invalid submission of listen_type 'playing_now' which contains
            timestamp 'listened_at'
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'playing_now_with_ts.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_playing_now_more_than_one_listen(self):
        """ Test for invalid submission of listen_type 'playing_now' which contains
            more than one listen in payload
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'playing_now_more_than_one_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_valid_import(self):
        """ Test for a valid submission of listen_type 'import'
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'valid_import.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)

    def test_too_large_listen(self):
        """ Test for invalid submission in which the overall size of the listens sent is more than
            10240 bytes
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'too_large_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_too_many_tags_in_listen(self):
        """ Test for invalid submission in which a listen contains more than the allowed
            number of tags in additional_info.
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'too_many_tags.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_too_long_tag(self):
        """ Test for invalid submission in which a listen contains a tag of length > 64
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'too_long_tag.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_invalid_release_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid release_mbid
            in additional_info
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'invalid_release_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_invalid_artist_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid artist_mbid
            in additional_info
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'invalid_artist_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_invalid_recording_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid recording_mbid
            in additional_info
        """
        with open(os.path.join(os.getcwd(), 'testdata', 'invalid_recording_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
