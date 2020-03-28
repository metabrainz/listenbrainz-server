import sys
import os
import uuid

from listenbrainz.tests.integration import IntegrationTestCase
from flask import url_for
from redis import Redis
import listenbrainz.db.user as db_user
import time
import json
from listenbrainz import config
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from influxdb import InfluxDBClient

class APITestCase(IntegrationTestCase):

    def setUp(self):
        super(APITestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')

    def tearDown(self):
        r = Redis(host=self.app.config['REDIS_HOST'], port=self.app.config['REDIS_PORT'])
        r.flushall()
        self.reset_influx_db()
        super(APITestCase, self).tearDown()

    def reset_influx_db(self):
        """ Resets the entire influx db """
        influx = InfluxDBClient(
            host=config.INFLUX_HOST,
            port=config.INFLUX_PORT,
            database=config.INFLUX_DB_NAME
        )
        influx.query('DROP DATABASE %s' % config.INFLUX_DB_NAME)
        influx.query('CREATE DATABASE %s' % config.INFLUX_DB_NAME)

    def test_get_listens(self):
        """ Test to make sure that the api sends valid listens on get requests.
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send a listen
        ts = int(time.time())
        payload['payload'][0]['listened_at'] = ts
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # This sleep allows for the influx subscriber to take its time in getting
        # the listen submitted from redis and writing it to influx.
        # Removing it causes an empty list of listens to be returned.
        time.sleep(2)

        url = url_for('api_v1.get_listens', user_name = self.user['musicbrainz_id'])
        response = self.client.get(url, query_string = {'count': '1'})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        # make sure user id is correct
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

        # make sure that count is 1 and list also contains 1 listen
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['listens']), 1)

        # make sure timestamp is the same as sent
        sent_time = payload['payload'][0]['listened_at']
        self.assertEqual(data['listens'][0]['listened_at'], sent_time)
        self.assertEqual(data['listens'][0]['track_metadata']['track_name'], 'Fade')
        self.assertEqual(data['listens'][0]['track_metadata']['artist_name'], 'Kanye West')
        self.assertEqual(data['listens'][0]['track_metadata']['release_name'], 'The Life of Pablo')

        # make sure that artist msid, release msid and recording msid are present in data
        self.assertTrue(is_valid_uuid(data['listens'][0]['recording_msid']))
        self.assertTrue(is_valid_uuid(data['listens'][0]['track_metadata']['additional_info']['artist_msid']))
        self.assertTrue(is_valid_uuid(data['listens'][0]['track_metadata']['additional_info']['release_msid']))

        # check for latest listen timestamp
        self.assertEqual(data['latest_listen_ts'], ts)

        # request with min_ts should work
        response = self.client.get(url, query_string = {'min_ts': int(time.time())})
        self.assert200(response)

        # request with max_ts lesser than the timestamp of the submitted listen
        # should not send back any listens, should report a good latest_listen timestamp
        response = self.client.get(url, query_string = {'max_ts': ts - 2})
        self.assert200(response)
        self.assertListEqual(response.json['payload']['listens'], [])
        self.assertEqual(response.json['payload']['latest_listen_ts'], ts)


        # check that recent listens are fetched correctly
        url = url_for('api_v1.get_recent_listens_for_user_list', user_list = self.user['musicbrainz_id'])
        response = self.client.get(url, query_string = {'limit': '1'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data['count'], 1)


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
        self.assertEqual(response.json['code'], 401)

        # request with invalid authorization header
        response = self.client.post(
            url_for('api_v1.submit_listen'),
            data = json.dumps(payload),
            headers = {'Authorization' : 'Token testtokenplsignore'},
            content_type = 'application/json'
        )
        self.assert401(response)
        self.assertEqual(response.json['code'], 401)

    def test_valid_single(self):
        """ Test for valid submissioon of listen_type listen
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

    def test_single_more_than_one_listen(self):
        """ Test for an invalid submission which has listen_type 'single' but
            more than one listen in payload
        """
        with open(self.path_to_data_file('single_more_than_one_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_valid_playing_now(self):
        """ Test for valid submission of listen_type 'playing_now'
        """
        with open(self.path_to_data_file('valid_playing_now.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assert200(r)
        self.assertEqual(r.json['payload']['count'], 1)


    def test_playing_now_with_duration(self):
        """ Test that playing now listens with durations expire
        """
        with open(self.path_to_data_file('playing_now_with_duration.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 1)
        self.assertEqual(r.json['payload']['listens'][0]['track_metadata']['track_name'], 'Fade')

        time.sleep(1.1)

        # should have expired by now
        r = self.client.get(url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 0)

    def test_playing_now_with_duration_ms(self):
        """ Test that playing now submissions with duration_ms also expire
        """
        with open(self.path_to_data_file('playing_now_with_duration_ms.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 1)
        self.assertEqual(r.json['payload']['listens'][0]['track_metadata']['track_name'], 'Fade')

        time.sleep(1.1)

        # should have expired by now
        r = self.client.get(url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 0)

    def test_playing_now_with_ts(self):
        """ Test for invalid submission of listen_type 'playing_now' which contains
            timestamp 'listened_at'
        """
        with open(self.path_to_data_file('playing_now_with_ts.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_playing_now_more_than_one_listen(self):
        """ Test for invalid submission of listen_type 'playing_now' which contains
            more than one listen in payload
        """
        with open(self.path_to_data_file('playing_now_more_than_one_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)


    def test_valid_import(self):
        """ Test for a valid submission of listen_type 'import'
        """
        with open(self.path_to_data_file('valid_import.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

    def test_too_large_listen(self):
        """ Test for invalid submission in which the overall size of the listens sent is more than
            10240 bytes
        """
        with open(self.path_to_data_file('too_large_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_too_many_tags_in_listen(self):
        """ Test for invalid submission in which a listen contains more than the allowed
            number of tags in additional_info.
        """
        with open(self.path_to_data_file('too_many_tags.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_too_long_tag(self):
        """ Test for invalid submission in which a listen contains a tag of length > 64
        """
        with open(self.path_to_data_file('too_long_tag.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_invalid_release_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid release_mbid
            in additional_info
        """
        with open(self.path_to_data_file('invalid_release_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_invalid_artist_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid artist_mbid
            in additional_info
        """
        with open(self.path_to_data_file('invalid_artist_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_invalid_recording_mbid(self):
        """ Test for invalid submission in which a listen contains an invalid recording_mbid
            in additional_info
        """
        with open(self.path_to_data_file('invalid_recording_mbid.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_additional_info(self):
        """ Test to make sure that user generated data present in additional_info field
            of listens is preserved
        """
        with open(self.path_to_data_file('additional_info.json'), 'r') as f:
            payload = json.load(f)

        payload['payload'][0]['listened_at'] = int(time.time())
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # wait for influx-writer to get its work done before getting the listen back
        time.sleep(2)

        url = url_for('api_v1.get_listens', user_name = self.user['musicbrainz_id'])
        response = self.client.get(url, query_string = {'count': '1'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_additional_info = payload['payload'][0]['track_metadata']['additional_info']
        received_additional_info = data['listens'][0]['track_metadata']['additional_info']
        self.assertEqual(sent_additional_info['best_song'], received_additional_info['best_song'])
        self.assertEqual(sent_additional_info['link1'], received_additional_info['link1'])
        self.assertEqual(sent_additional_info['link2'], received_additional_info['link2'])
        self.assertEqual(sent_additional_info['other_stuff'], received_additional_info['other_stuff'])
        self.assertEqual(sent_additional_info['nested']['info'], received_additional_info['nested.info'])
        self.assertListEqual(sent_additional_info['release_type'], received_additional_info['release_type'])
        self.assertEqual(sent_additional_info['spotify_id'], received_additional_info['spotify_id'])
        self.assertEqual(sent_additional_info['isrc'], received_additional_info['isrc'])
        self.assertEqual(int(sent_additional_info['tracknumber']), received_additional_info['tracknumber'])
        self.assertEqual(sent_additional_info['release_group_mbid'], received_additional_info['release_group_mbid'])
        self.assertListEqual(sent_additional_info['work_mbids'], received_additional_info['work_mbids'])
        self.assertListEqual(sent_additional_info['artist_mbids'], received_additional_info['artist_mbids'])
        self.assertListEqual(sent_additional_info['non_official_list'], received_additional_info['non_official_list'])

        self.assertNotIn('track_name', sent_additional_info)
        self.assertNotIn('artist_name', sent_additional_info)
        self.assertNotIn('release_name', sent_additional_info)


    def test_latest_import(self):
        """ Test for api.latest_import """

        # initially the value of latest_import will be 0
        response = self.client.get(url_for('api_v1.latest_import'), query_string={'user_name': self.user['musicbrainz_id']})
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(data['latest_import'], 0)

        # now an update
        val = int(time.time())
        response = self.client.post(
            url_for('api_v1.latest_import'),
            data=json.dumps({'ts': val}),
            headers={'Authorization': 'Token {token}'.format(token=self.user['auth_token'])}
        )
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # now the value must have changed
        response = self.client.get(url_for('api_v1.latest_import'), query_string={'user_name': self.user['musicbrainz_id']})
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(data['latest_import'], val)

    def test_latest_import_unauthorized(self):
        """ Test for invalid tokens passed to user.latest_import view"""

        val = int(time.time())
        response = self.client.post(
            url_for('api_v1.latest_import'),
            data=json.dumps({'ts': val}),
            headers={'Authorization': 'Token thisisinvalid'}
        )
        self.assert401(response)
        self.assertEqual(response.json['code'], 401)

    def test_latest_import_unknown_user(self):
        """Tests api.latest_import without a valid username"""
        response = self.client.get(url_for('api_v1.latest_import'), query_string={'user_name': ''})
        self.assert404(response)
        self.assertEqual(response.json['code'], 404)

    def test_multiple_artist_names(self):
        """ Tests multiple artist names in artist_name field of data """

        with open(self.path_to_data_file('artist_name_list.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('artist_name must be a single string.', response.json['error'])

    def test_too_high_timestamps(self):
        """ Tests for timestamps greater than current time """

        with open(self.path_to_data_file('timestamp_in_ns.json'), 'r') as f:
            payload = json.load(f)
        payload['listened_at'] = int(time.time()) * 10**9
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('Value for key listened_at is too high.', response.json['error'])

    def test_invalid_token_validation(self):
        """Sends an invalid token to api.validate_token"""
        url = url_for('api_v1.validate_token')
        response = self.client.get(url, query_string = {"token":"invalidtoken"})
        self.assert200(response)
        self.assertEqual(response.json['code'], 200)
        self.assertEqual('Token invalid.', response.json['message'])
        self.assertFalse(response.json['valid'])
        self.assertNotIn('user_name', response.json)


    def test_valid_token_validation(self):
        """Sends a valid token to api.validate_token"""
        url = url_for('api_v1.validate_token')
        response = self.client.get(url, query_string = {"token":self.user['auth_token']})
        self.assert200(response)
        self.assertEqual(response.json['code'], 200)
        self.assertEqual('Token valid.', response.json['message'])
        self.assertTrue(response.json['valid'])
        self.assertEqual(response.json['user_name'], self.user['musicbrainz_id'])


    def test_get_playing_now(self):
        """ Test for valid submission and retrieval of listen_type 'playing_now'
        """
        r = self.client.get(url_for('api_v1.get_playing_now', user_name='thisuserdoesnotexist'))
        self.assert404(r)

        r = self.client.get(url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 0)
        self.assertEqual(len(r.json['payload']['listens']), 0)

        with open(self.path_to_data_file('valid_playing_now.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assertTrue(r.json['payload']['playing_now'])
        self.assertEqual(r.json['payload']['count'], 1)
        self.assertEqual(len(r.json['payload']['listens']), 1)
        self.assertEqual(r.json['payload']['user_id'], self.user['musicbrainz_id'])
        self.assertEqual(r.json['payload']['listens'][0]['track_metadata']['artist_name'], 'Kanye West')
        self.assertEqual(r.json['payload']['listens'][0]['track_metadata']['release_name'], 'The Life of Pablo')
        self.assertEqual(r.json['payload']['listens'][0]['track_metadata']['track_name'], 'Fade')
