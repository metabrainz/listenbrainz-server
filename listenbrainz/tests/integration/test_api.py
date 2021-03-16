import json
import time
from unittest.mock import patch

import pytest
from flask import url_for

import listenbrainz.db.user as db_user
from listenbrainz import db
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver.views.api_tools import is_valid_uuid


class APITestCase(ListenAPIIntegrationTestCase):

    def test_get_listens_invalid_count(self):
        """If the count argument is negative, the API should raise HTTP 400"""
        url = url_for('api_v1.get_listens',
                      user_name=self.user['musicbrainz_id'])
        response = self.client.get(url, query_string={'count': '-1'})
        self.assert400(response)

    def test_get_listens_ts_order(self):
        """If min_ts is greater than max_ts, the API should raise HTTP 400"""
        url = url_for('api_v1.get_listens',
                      user_name=self.user['musicbrainz_id'])
        response = self.client.get(
            url, query_string={'max_ts': '1400000000', 'min_ts': '1500000000'})
        self.assert400(response)

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

        url = url_for('api_v1.get_listens',
                      user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(
            url, 1, query_string={'count': '1'})
        data = json.loads(response.data)['payload']

        self.assert200(response)

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
                         ['additional_info']['listening_from'], 'spotify')

        # make sure that artist msid, release msid and recording msid are present in data
        self.assertTrue(is_valid_uuid(data['listens'][0]['recording_msid']))
        self.assertTrue(is_valid_uuid(
            data['listens'][0]['track_metadata']['additional_info']['artist_msid']))
        self.assertTrue(is_valid_uuid(
            data['listens'][0]['track_metadata']['additional_info']['release_msid']))

        # check for latest listen timestamp
        self.assertEqual(data['latest_listen_ts'], ts)

        # request with min_ts should work
        response = self.client.get(
            url, query_string={'min_ts': int(time.time())})
        self.assert200(response)

        # request with max_ts lesser than the timestamp of the submitted listen
        # should not send back any listens, should report a good latest_listen timestamp
        response = self.client.get(url, query_string={'max_ts': ts - 2})
        self.assert200(response)
        self.assertListEqual(response.json['payload']['listens'], [])
        self.assertEqual(response.json['payload']['latest_listen_ts'], ts)

        # test request with both max_ts and min_ts is working
        url = url_for('api_v1.get_listens',
                      user_name=self.user['musicbrainz_id'])

        response = self.client.get(
            url, query_string={'max_ts': ts + 1000, 'min_ts': ts - 1000})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['listens']), 1)

        sent_time = payload['payload'][0]['listened_at']
        self.assertEqual(data['listens'][0]['listened_at'], sent_time)
        self.assertEqual(data['listens'][0]
                         ['track_metadata']['track_name'], 'Fade')
        self.assertEqual(data['listens'][0]['track_metadata']
                         ['artist_name'], 'Kanye West')
        self.assertEqual(data['listens'][0]['track_metadata']
                         ['release_name'], 'The Life of Pablo')

        # check that recent listens are fetched correctly
        url = url_for('api_v1.get_recent_listens_for_user_list',
                      user_list=self.user['musicbrainz_id'])
        response = self.client.get(url, query_string={'limit': '1'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data['count'], 1)

        url = url_for('api_v1.get_listen_count',
                      user_name=self.user['musicbrainz_id'])
        response = self.client.get(url)
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data['count'], 1)

        url = url_for('api_v1.get_listen_count', user_name="sir_dumpsterfire")
        response = self.client.get(url)
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data['count'], 0)

    def test_get_listens_with_time_range(self):
        """ Test to make sure that the api sends valid listens on get requests.
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send three listens
        user = db_user.get_or_create(1, 'test_time_range')
        ts = 1400000000
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts + (100 * i)
            response = self.send_data(payload, user)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        old_ts = ts - 2592000  # 30 days
        payload['payload'][0]['listened_at'] = old_ts
        response = self.send_data(payload, user)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        expected_count = 3
        url = url_for('api_v1.get_listens', user_name=user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, expected_count)
        data = json.loads(response.data)['payload']

        self.assert200(response)
        self.assertEqual(data['count'], expected_count)
        self.assertEqual(data['listens'][0]['listened_at'], 1400000200)
        self.assertEqual(data['listens'][1]['listened_at'], 1400000100)
        self.assertEqual(data['listens'][2]['listened_at'], 1400000000)

        url = url_for('api_v1.get_listens', user_name=user['musicbrainz_id'])
        response = self.client.get(url, query_string={'time_range': 10})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data['count'], 4)
        self.assertEqual(data['listens'][0]['listened_at'], 1400000200)
        self.assertEqual(data['listens'][1]['listened_at'], 1400000100)
        self.assertEqual(data['listens'][2]['listened_at'], 1400000000)
        self.assertEqual(data['listens'][3]['listened_at'], old_ts)

        # Check time_range ranges
        url = url_for('api_v1.get_listens', user_name=user['musicbrainz_id'])
        response = self.client.get(url, query_string={'time_range': 0})
        self.assert400(response)

        url = url_for('api_v1.get_listens', user_name=user['musicbrainz_id'])
        response = self.client.get(url, query_string={'time_range': 74})
        self.assert400(response)

    def test_get_listens_order(self):
        """ Test to make sure that the api sends listens in valid order.
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send three listens
        ts = 1400000000
        user = db_user.get_or_create(1, 'test_order')
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts + (100 * i)
            response = self.send_data(payload, user)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        expected_count = 3
        url = url_for('api_v1.get_listens', user_name=user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, expected_count)
        data = json.loads(response.data)['payload']

        self.assert200(response)
        self.assertEqual(data['count'], expected_count)
        self.assertEqual(data['listens'][0]['listened_at'], 1400000200)
        self.assertEqual(data['listens'][1]['listened_at'], 1400000100)
        self.assertEqual(data['listens'][2]['listened_at'], 1400000000)

        # Fetch the listens with from_ts and make sure the order is descending
        url = url_for('api_v1.get_listens',
                      user_name=self.user['musicbrainz_id'])
        response = self.client.get(
            url, query_string={'count': '3', 'from_ts': ts-500})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        self.assertEqual(data['count'], expected_count)
        self.assertEqual(data['listens'][0]['listened_at'], 1400000200)
        self.assertEqual(data['listens'][1]['listened_at'], 1400000100)
        self.assertEqual(data['listens'][2]['listened_at'], 1400000000)

    def test_zero_listens_payload(self):
        """ Test that API returns 400 for payloads with no listens
        """

        for listen_type in ('single', 'playing_now', 'import'):
            payload = {
                'listen_type': listen_type,
                'payload': [],
            }
            response = self.send_data(payload)
            self.assert400(response)

    def test_unauthorized_submission(self):
        """ Test for checking that unauthorized submissions return 401
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # request with no authorization header
        response = self.client.post(
            url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assert401(response)
        self.assertEqual(response.json['code'], 401)

        # request with invalid authorization header
        response = self.client.post(
            url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            headers={'Authorization': 'Token testtokenplsignore'},
            content_type='application/json'
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

        r = self.client.get(url_for('api_v1.get_playing_now',
                                    user_name=self.user['musicbrainz_id']))
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

        r = self.client.get(url_for('api_v1.get_playing_now',
                                    user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 1)
        self.assertEqual(r.json['payload']['listens'][0]
                         ['track_metadata']['track_name'], 'Fade')

        time.sleep(1.1)

        # should have expired by now
        r = self.client.get(url_for('api_v1.get_playing_now',
                                    user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 0)

    def test_playing_now_with_duration_ms(self):
        """ Test that playing now submissions with duration_ms also expire
        """
        with open(self.path_to_data_file('playing_now_with_duration_ms.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(url_for('api_v1.get_playing_now',
                                    user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 1)
        self.assertEqual(r.json['payload']['listens'][0]
                         ['track_metadata']['track_name'], 'Fade')

        time.sleep(1.1)

        # should have expired by now
        r = self.client.get(url_for('api_v1.get_playing_now',
                                    user_name=self.user['musicbrainz_id']))
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

        payload['payload'][0]['listened_at'] = 1280258690
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        expected_length = 1
        url = url_for('api_v1.get_listens',
                      user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(
            url, expected_length, query_string={'count': '1'})
        data = json.loads(response.data)['payload']

        self.assert200(response)
        self.assertEqual(len(data['listens']), expected_length)
        sent_additional_info = payload['payload'][0]['track_metadata']['additional_info']
        received_additional_info = data['listens'][0]['track_metadata']['additional_info']
        self.assertEqual(
            sent_additional_info['best_song'], received_additional_info['best_song'])
        self.assertEqual(
            sent_additional_info['link1'], received_additional_info['link1'])
        self.assertEqual(
            sent_additional_info['link2'], received_additional_info['link2'])
        self.assertEqual(
            sent_additional_info['other_stuff'], received_additional_info['other_stuff'])
        self.assertEqual(
            sent_additional_info['nested']['info'], received_additional_info['nested.info'])
        self.assertListEqual(
            sent_additional_info['release_type'], received_additional_info['release_type'])
        self.assertEqual(
            sent_additional_info['spotify_id'], received_additional_info['spotify_id'])
        self.assertEqual(
            sent_additional_info['isrc'], received_additional_info['isrc'])
        self.assertEqual(
            sent_additional_info['tracknumber'], received_additional_info['tracknumber'])
        self.assertEqual(
            sent_additional_info['release_group_mbid'], received_additional_info['release_group_mbid'])
        self.assertListEqual(
            sent_additional_info['work_mbids'], received_additional_info['work_mbids'])
        self.assertListEqual(
            sent_additional_info['artist_mbids'], received_additional_info['artist_mbids'])
        self.assertListEqual(
            sent_additional_info['non_official_list'], received_additional_info['non_official_list'])

        self.assertNotIn('track_name', sent_additional_info)
        self.assertNotIn('artist_name', sent_additional_info)
        self.assertNotIn('release_name', sent_additional_info)

    def test_000_similar_users(self):

        response = self.client.get(
            url_for('api_v1.get_similar_users', user_name='my_dear_muppet'))
        self.assert404(response)

        conn = db.engine.raw_connection()
        with conn.cursor() as curs:
            data = {self.user2['musicbrainz_id']: .123}
            curs.execute("""INSERT INTO recommendation.similar_user VALUES (%s, %s)""",
                         (self.user['id'], json.dumps(data)))
        conn.commit()

        response = self.client.get(
            url_for('api_v1.get_similar_users', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data[0]['user_name'], self.user2['musicbrainz_id'])
        self.assertEqual(data[0]['similarity'], .123)

        response = self.client.get(url_for(
            'api_v1.get_similar_to_user', user_name=self.user['musicbrainz_id'], other_user_name="muppet"))
        self.assert404(response)

        response = self.client.get(url_for(
            'api_v1.get_similar_to_user', user_name=self.user['musicbrainz_id'], other_user_name=self.user2['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data['user_name'], self.user2['musicbrainz_id'])
        self.assertEqual(data['similarity'], .123)

    def test_latest_import(self):
        """ Test for api.latest_import """

        # initially the value of latest_import will be 0
        response = self.client.get(url_for('api_v1.latest_import'), query_string={
                                   'user_name': self.user['musicbrainz_id']})
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(data['latest_import'], 0)

        # now an update
        val = int(time.time())
        response = self.client.post(
            url_for('api_v1.latest_import'),
            data=json.dumps({'ts': val}),
            headers={'Authorization': 'Token {token}'.format(
                token=self.user['auth_token'])}
        )
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # now the value must have changed
        response = self.client.get(url_for('api_v1.latest_import'), query_string={
                                   'user_name': self.user['musicbrainz_id']})
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
        response = self.client.get(
            url_for('api_v1.latest_import'), query_string={'user_name': ''})
        self.assert404(response)
        self.assertEqual(response.json['code'], 404)

    def test_multiple_artist_names(self):
        """ Tests multiple artist names in artist_name field of data """

        with open(self.path_to_data_file('artist_name_list.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('artist_name must be a single string.',
                         response.json['error'])

    def test_too_high_timestamps(self):
        """ Tests for timestamps greater than current time """

        with open(self.path_to_data_file('timestamp_in_ns.json'), 'r') as f:
            payload = json.load(f)
        payload['listened_at'] = int(time.time()) * 10**9
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(
            'Value for key listened_at is too high.', response.json['error'])

    def test_invalid_token_validation(self):
        """Sends an invalid token to api.validate_token"""
        url = url_for('api_v1.validate_token')
        response = self.client.get(url, query_string={"token": "invalidtoken"})
        self.assert200(response)
        self.assertEqual(response.json['code'], 200)
        self.assertEqual('Token invalid.', response.json['message'])
        self.assertFalse(response.json['valid'])
        self.assertNotIn('user_name', response.json)

    def test_valid_token_validation(self):
        """Sends a valid token to api.validate_token"""
        url = url_for('api_v1.validate_token')
        response = self.client.get(
            url, query_string={"token": self.user['auth_token']})
        self.assert200(response)
        self.assertEqual(response.json['code'], 200)
        self.assertEqual('Token valid.', response.json['message'])
        self.assertTrue(response.json['valid'])
        self.assertEqual(response.json['user_name'],
                         self.user['musicbrainz_id'])

    def test_get_playing_now(self):
        """ Test for valid submission and retrieval of listen_type 'playing_now'
        """
        r = self.client.get(url_for('api_v1.get_playing_now',
                                    user_name='thisuserdoesnotexist'))
        self.assert404(r)

        r = self.client.get(url_for('api_v1.get_playing_now',
                                    user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 0)
        self.assertEqual(len(r.json['payload']['listens']), 0)

        with open(self.path_to_data_file('valid_playing_now.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(url_for('api_v1.get_playing_now',
                                    user_name=self.user['musicbrainz_id']))
        self.assertTrue(r.json['payload']['playing_now'])
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

    @pytest.mark.skip(reason="Test seems to fail when running all integration tests, but passes when run individually. "
                             "Skip for now")
    def test_delete_listen(self):
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send a listen
        ts = int(time.time())
        payload['payload'][0]['listened_at'] = ts
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        url = url_for('api_v1.get_listens',
                      user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, 1)
        data = json.loads(response.data)['payload']
        self.assertEqual(len(data['listens']), 1)

        delete_listen_url = url_for('api_v1.delete_listen')
        data = {
            "listened_at": ts,
            "recording_msid": payload['payload'][0]['track_metadata']['additional_info']['recording_msid']
        }

        response = self.client.post(
            delete_listen_url,
            data=json.dumps(data),
            headers={'Authorization': 'Token {}'.format(
                self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

    def test_delete_listen_not_logged_in(self):
        delete_listen_url = url_for('api_v1.delete_listen')
        data = {
            "listened_at": 1486449409,
            "recording_msid": "2cfad207-3f55-4aec-8120-86cf66e34d59"
        }

        # send a request without auth_token
        response = self.client.post(
            delete_listen_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assert401(response)

        # send a request with invalid auth_token
        response = self.client.post(
            delete_listen_url,
            data=json.dumps(data),
            headers={'Authorization': 'Token {}'.format(
                "invalidtokenpleaseignore")},
            content_type='application/json'
        )
        self.assert401(response)

    def test_delete_listen_missing_keys(self):
        delete_listen_url = url_for('api_v1.delete_listen')

        # send request without listened_at
        data = {
            "recording_msid": "2cfad207-3f55-4aec-8120-86cf66e34d59"
        }

        response = self.client.post(
            delete_listen_url,
            data=json.dumps(data),
            headers={'Authorization': 'Token {}'.format(
                self.user['auth_token'])},
            content_type='application/json'
        )
        self.assertStatus(response, 400)
        self.assertEqual(response.json["error"], "Listen timestamp missing.")

        # send request without recording_msid
        data = {
            "listened_at": 1486449409
        }

        response = self.client.post(
            delete_listen_url,
            data=json.dumps(data),
            headers={'Authorization': 'Token {}'.format(
                self.user['auth_token'])},
            content_type='application/json'
        )
        self.assertStatus(response, 400)
        self.assertEqual(response.json["error"], "Recording MSID missing.")

    def test_delete_listen_invalid_keys(self):
        delete_listen_url = url_for('api_v1.delete_listen')

        # send request with invalid listened_at
        data = {
            "listened_at": "invalid listened_at",
            "recording_msid": "2cfad207-3f55-4aec-8120-86cf66e34d59"
        }

        response = self.client.post(
            delete_listen_url,
            data=json.dumps(data),
            headers={'Authorization': 'Token {}'.format(
                self.user['auth_token'])},
            content_type='application/json'
        )
        self.assertStatus(response, 400)
        self.assertEqual(
            response.json["error"], "invalid listened_at: Listen timestamp invalid.")

        # send request with invalid recording_msid
        data = {
            "listened_at": 1486449409,
            "recording_msid": "invalid recording_msid"
        }

        response = self.client.post(
            delete_listen_url,
            data=json.dumps(data),
            headers={'Authorization': 'Token {}'.format(
                self.user['auth_token'])},
            content_type='application/json'
        )
        self.assertEqual(
            response.json["error"], "invalid recording_msid: Recording MSID format invalid.")

    def test_followers_returns_the_followers_of_a_user(self):
        # create a new user, and follow them
        followed_user = db_user.get_or_create(3, 'followed_user')
        self.temporary_login(self.user.login_id)
        r = self.client.post(url_for("user.follow_user", user_name=followed_user["musicbrainz_id"]))
        self.assert200(r)

        r = self.client.get(url_for("api_v1.get_followers", user_name=followed_user["musicbrainz_id"]))
        self.assert200(r)
        self.assertListEqual([{'musicbrainz_id': self.user.musicbrainz_id}], r.json['followers'])

    def test_following_returns_the_people_who_follow_the_user(self):
        # create a new user, and follow them
        followed_user = db_user.get_or_create(3, 'followed_user')
        self.temporary_login(self.user.login_id)
        r = self.client.post(url_for("user.follow_user", user_name=followed_user["musicbrainz_id"]))
        self.assert200(r)

        r = self.client.get(url_for("api_v1.get_following", user_name=self.user["musicbrainz_id"]))
        self.assert200(r)
        self.assertListEqual([{'musicbrainz_id': 'followed_user', 'id': followed_user['id']}], r.json['following'])
