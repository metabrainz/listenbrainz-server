from __future__ import absolute_import, print_function
import sys
import os
import uuid

from listenbrainz.tests.integration import IntegrationTestCase
from flask import url_for
import listenbrainz.db.user as db_user
import time
import json
from listenbrainz.webserver.views.api_tools import is_valid_uuid

class APITestCase(IntegrationTestCase):

    def setUp(self):
        super(APITestCase, self).setUp()
        self.user = db_user.get_or_create('testuserpleaseignore')

    def test_get_listens(self):
        """ Test to make sure that the api sends valid listens on get requests.
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send a listen
        payload['payload'][0]['listened_at'] = int(time.time())
        response = self.send_data(payload)
        self.assert200(response)

        # This sleep allows for the influx subscriber to take its time in getting
        # the listen submitted from redis and writing it to influx.
        # Removing it causes an empty list of listens to be returned.
        time.sleep(15)

        url = url_for('api_v1.get_listens', user_name = self.user['musicbrainz_id'])
        response = self.client.get(url, query_string = {'count': '1'})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        # make sure user id is correct
        self.assertEquals(data['user_id'], self.user['musicbrainz_id'])

        # make sure that count is 1 and list also contains 1 listen
        self.assertEquals(data['count'], 1)
        self.assertEquals(len(data['listens']), 1)

        # make sure timestamp is the same as sent
        sent_time = payload['payload'][0]['listened_at']
        self.assertEquals(data['listens'][0]['listened_at'], sent_time)

        # make sure that artist msid, release msid and recording msid are present in data
        self.assertTrue(is_valid_uuid(data['listens'][0]['recording_msid']))
        self.assertTrue(is_valid_uuid(data['listens'][0]['track_metadata']['additional_info']['artist_msid']))
        self.assertTrue(is_valid_uuid(data['listens'][0]['track_metadata']['additional_info']['release_msid']))

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
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
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
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)

    def test_single_more_than_one_listen(self):
        """ Test for an invalid submission which has listen_type 'single' but
            more than one listen in payload
        """
        with open(self.path_to_data_file('single_more_than_one_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_valid_playing_now(self):
        """ Test for valid submission of listen_type 'playing_now'
        """
        with open(self.path_to_data_file('valid_playing_now.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)

    def test_playing_now_with_ts(self):
        """ Test for invalid submission of listen_type 'playing_now' which contains
            timestamp 'listened_at'
        """
        with open(self.path_to_data_file('playing_now_with_ts.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_playing_now_more_than_one_listen(self):
        """ Test for invalid submission of listen_type 'playing_now' which contains
            more than one listen in payload
        """
        with open(self.path_to_data_file('playing_now_more_than_one_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_valid_import(self):
        """ Test for a valid submission of listen_type 'import'
        """
        with open(self.path_to_data_file('valid_import.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)

    def test_too_large_listen(self):
        """ Test for invalid submission in which the overall size of the listens sent is more than
            10240 bytes
        """
        with open(self.path_to_data_file('too_large_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_too_many_tags_in_listen(self):
        """ Test for invalid submission in which a listen contains more than the allowed
            number of tags in additional_info.
        """
        with open(self.path_to_data_file('too_many_tags.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_too_long_tag(self):
        """ Test for invalid submission in which a listen contains a tag of length > 64
        """
        with open(self.path_to_data_file('too_long_tag.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_invalid_release_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid release_mbid
            in additional_info
        """
        with open(self.path_to_data_file('invalid_release_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_invalid_artist_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid artist_mbid
            in additional_info
        """
        with open(self.path_to_data_file('invalid_artist_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_invalid_recording_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid recording_mbid
            in additional_info
        """
        with open(self.path_to_data_file('invalid_recording_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_additional_info(self):
        """ Test to make sure that user generated data present in additional_info field
            of listens is preserved
        """
        with open(self.path_to_data_file('additional_info.json'), 'r') as f:
            payload = json.load(f)

        payload['payload'][0]['listened_at'] = int(time.time())
        response = self.send_data(payload)
        self.assert200(response)

        # wait for influx-writer to get its work done before getting the listen back
        time.sleep(15)

        url = url_for('api_v1.get_listens', user_name = self.user['musicbrainz_id'])
        response = self.client.get(url, query_string = {'count': '1'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_additional_info = payload['payload'][0]['track_metadata']['additional_info']
        received_additional_info = data['listens'][0]['track_metadata']['additional_info']
        self.assertEquals(sent_additional_info['best_song'], received_additional_info['best_song'])
        self.assertEquals(sent_additional_info['link1'], received_additional_info['link1'])
        self.assertEquals(sent_additional_info['link2'], received_additional_info['link2'])
        self.assertEquals(sent_additional_info['other_stuff'], received_additional_info['other_stuff'])
        self.assertEquals(sent_additional_info['nested']['info'], received_additional_info['nested.info'])
