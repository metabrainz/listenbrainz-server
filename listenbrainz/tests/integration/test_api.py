import json
import time
from unittest.mock import patch

import pytest

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
from data.model.external_service import ExternalServiceType
from listenbrainz import db
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.webserver.views.api_tools import is_valid_uuid
import listenbrainz.db.external_service_oauth as db_oauth
from listenbrainz.webserver.views.playlist_api import PLAYLIST_EXTENSION_URI, PlaylistAPIXMLError


class APITestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super(APITestCase, self).setUp()
        self.followed_user = db_user.get_or_create(self.db_conn, 3, 'followed_user')
        self.follow_user_url = self.custom_url_for("social_api_v1.follow_user",
                                                   user_name=self.followed_user["musicbrainz_id"])
        self.follow_user_headers = {'Authorization': 'Token {}'.format(self.user['auth_token'])}

    def test_get_listens_invalid_count(self):
        """If the count argument is negative, the API should raise HTTP 400"""
        url = self.custom_url_for('api_v1.get_listens',
                                  user_name=self.user['musicbrainz_id'])
        response = self.client.get(url, query_string={'count': '-1'})
        self.assert400(response)

    def test_get_listens_ts_order(self):
        """If min_ts is greater than max_ts, the API should raise HTTP 400"""
        url = self.custom_url_for('api_v1.get_listens',
                                  user_name=self.user['musicbrainz_id'])
        response = self.client.get(
            url, query_string={'max_ts': '1400000000', 'min_ts': '1500000000'})
        self.assert400(response)

    @patch("listenbrainz.webserver.timescale_connection._ts", None)
    def test_get_listens_ts_unavailable(self):
        """Check that an error message is returned if the listenstore is unavailable"""
        url = self.custom_url_for('api_v1.get_listens',
                                  user_name=self.user['musicbrainz_id'])
        response = self.client.get(url)
        self.assertStatus(response, 503)

    def test_get_listens(self):
        """ Test to make sure that the api sends valid listens on get requests.
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send a listen
        ts = int(time.time())
        payload['payload'][0]['listened_at'] = ts
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        url = self.custom_url_for('api_v1.get_listens',
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
                         ['additional_info']['music_service'], 'spotify.com')

        # make sure that artist msid, release msid and recording msid are present in data
        self.assertTrue(is_valid_uuid(data['listens'][0]['recording_msid']))

        # check for latest and oldest  listen timestamp
        self.assertEqual(data['latest_listen_ts'], ts)
        self.assertEqual(data['oldest_listen_ts'], ts)

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
        self.assertEqual(response.json['payload']['oldest_listen_ts'], ts)

        # test request with both max_ts and min_ts is working
        url = self.custom_url_for('api_v1.get_listens',
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

        url = self.custom_url_for('api_v1.get_listen_count',
                                  user_name=self.user['musicbrainz_id'])
        response = self.client.get(url)
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data['count'], 1)

        url = self.custom_url_for('api_v1.get_listen_count', user_name="sir_dumpsterfire")
        response = self.client.get(url)
        self.assert404(response)

    def test_get_listens_order(self):
        """ Test to make sure that the api sends listens in valid order.
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send three listens
        ts = 1400000000
        user = db_user.get_or_create(self.db_conn, 1, 'test_order')
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts + (100 * i)
            response = self.send_data(payload, user, recalculate=True)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        expected_count = 3
        url = self.custom_url_for('api_v1.get_listens', user_name=user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, expected_count)
        data = json.loads(response.data)['payload']

        self.assert200(response)
        self.assertEqual(data['count'], expected_count)
        self.assertEqual(data['listens'][0]['listened_at'], 1400000200)
        self.assertEqual(data['listens'][1]['listened_at'], 1400000100)
        self.assertEqual(data['listens'][2]['listened_at'], 1400000000)

        # Fetch the listens with from_ts and make sure the order is descending
        url = self.custom_url_for('api_v1.get_listens',
                                  user_name=self.user['musicbrainz_id'])
        response = self.client.get(
            url, query_string={'count': '3', 'from_ts': ts - 500})
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

    def test_payload_is_not_list(self):
        """ Test that API returns 400 for payloads with no listens
        """
        for listen_type in ('single', 'playing_now', 'import'):
            data = {
                'listen_type': listen_type,
                'payload': {},
            }
            response = self.send_data(data)
            self.assert400(response)
            self.assertEqual('The payload in the JSON document should be'
                             ' a list of listens.', response.json['error'])

    def test_top_level_json_is_not_dict(self):
        for data in (1, False, None, [2, 3], "foobar"):
            response = self.send_data(data)
            self.assert400(response)
            self.assertEqual("Invalid JSON document submitted. Top level of JSON "
                             "document should be a json object.", response.json["error"])

    def test_unauthorized_submission(self):
        """ Test for checking that unauthorized submissions return 401
        """
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # request with no authorization header
        response = self.client.post(
            self.custom_url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assert401(response)
        self.assertEqual(response.json['code'], 401)

        # request with invalid authorization header
        response = self.client.post(
            self.custom_url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            headers={'Authorization': 'Token testtokenplsignore'},
            content_type='application/json'
        )
        self.assert401(response)
        self.assertEqual(response.json['code'], 401)

    def test_valid_single(self):
        """ Test for valid submissioon of listen_type listen """
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
    
    def test_playlist_api_xml_error(self):

        # Making a request that would trigger the error
        response = self.client.get('/1/playlist/-6924291-8b14-726253c14f12/xspf')
        self.assertEqual(response.status_code, 400)

        # Checkinging if the response is in XML format and contains the correct error message and code
        expected_xml = """
<?xml version="1.0" encoding="utf-8"?>
<playlist_error>
<error code="400">Provided playlist ID is invalid.</error>
</playlist_error>
""".strip()

        first_xml_str = ''.join(response.data.decode('utf-8').split())
        second_xml_str = ''.join(expected_xml.split())
        self.assertEqual(first_xml_str, second_xml_str)

    def test_playlist_api_xml_auth_error(self):
        # Testing for 401: Authorization Error
        playlist = {
            "playlist": {
                "title": "you're a person",
                "extension": {
                     PLAYLIST_EXTENSION_URI: {
                         "public": True,
                    }
                }
            }
        }

        response_post = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        playlist_mbid = response_post.json["playlist_mbid"]

        r = self.client.get(
            self.custom_url_for('playlist_api_v1.get_playlist_xspf', playlist_mbid=playlist_mbid),
            headers={'Authorization': 'Token testtokenplsignore'}
        )
        self.assertEqual(r.status_code, 401)

        expected_error_xml = """
<?xml version="1.0" encoding="utf-8"?>
<playlist_error>
<error code="401">Invalid authorization token.</error>
</playlist_error>
""".strip().replace('\n', '').replace('    ', '')
        
        first_xml_str_auth = ''.join(r.data.decode('utf-8').split())
        second_xml_str_auth = ''.join(expected_error_xml.split())
        self.assertEqual(first_xml_str_auth, second_xml_str_auth)

    def test_playlist_api_xml_internal_server_error(self):
        
        playlist = {
            "playlist": {
                "title": "you're a person",
                "extension": {
                     PLAYLIST_EXTENSION_URI: {
                         "public": True,
                    }
                }
            }
        }

        response_post = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        playlist_mbid = response_post.json["playlist_mbid"]

        with patch('listenbrainz.webserver.views.playlist_api.fetch_playlist_recording_metadata') as mock_fetch_metadata:
            mock_fetch_metadata.side_effect = PlaylistAPIXMLError("Internal server error occurred.")

            # Request that would trigger mocked error
            response = self.client.get(f'/1/playlist/{playlist_mbid}/xspf')

            # Assert that a 500 Internal Server Error is returned
            self.assertEqual(response.status_code, 500)

            # The expected XML error response
            expected_error_xml = """<?xml version="1.0" encoding="utf-8"?>
<playlist_error>
  <error code="500">Internal server error occurred.</error>
</playlist_error>"""
            
            actual_xml = response.data.decode('utf-8')
            self.assertEqual(actual_xml, expected_error_xml)


    def test_valid_playing_now(self):
        """ Test for valid submission of listen_type 'playing_now'
        """
        with open(self.path_to_data_file('valid_playing_now.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(self.custom_url_for('api_v1.get_playing_now',
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

        r = self.client.get(self.custom_url_for('api_v1.get_playing_now',
                                                user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 1)
        self.assertEqual(r.json['payload']['listens'][0]
                         ['track_metadata']['track_name'], 'Fade')

        time.sleep(1.1)

        # should have expired by now
        r = self.client.get(self.custom_url_for('api_v1.get_playing_now', user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 0)

    def test_playing_now_with_duration_ms(self):
        """ Test that playing now submissions with duration_ms also expire
        """
        with open(self.path_to_data_file('playing_now_with_duration_ms.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(self.custom_url_for('api_v1.get_playing_now',
                                                user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 1)
        self.assertEqual(r.json['payload']['listens'][0]
                         ['track_metadata']['track_name'], 'Fade')

        time.sleep(1.1)

        # should have expired by now
        r = self.client.get(self.custom_url_for('api_v1.get_playing_now',
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
        self.assertTrue("JSON document is too large." in response.json['error'])

        # This document is 45kb, increase it to over 10k kb
        payload['payload'] = payload['payload'] * 300
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertTrue("Payload too large." in response.json['error'])

    def test_too_many_listens(self):
        """ Test for invalid submission in which more than 1000 listens are in a single request
        """
        with open(self.path_to_data_file('valid_import.json'), 'r') as f:
            payload = json.load(f)

        # 2 messages in this file, * 500 to make more up to 1000
        payload['payload'] = payload['payload'] * 500 + payload['payload']
        self.assertEqual(len(payload['payload']), 1002)

        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertTrue("Too many listens" in response.json['error'])

    def test_empty_track_name(self):
        """ Test for invalid submission in which a listen contains an empty track name
        """
        with open(self.path_to_data_file('empty_track_name.json'), 'r') as f:
            payload = json.load(f)

        del payload["payload"][0]["track_metadata"]["track_name"]
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_invalid_release_name(self):
        with open(self.path_to_data_file('invalid_release_name.json'), 'r') as f:
            payload = json.load(f)

        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['error'], "track_metadata.release_name must be a single string.")

    def test_bad_track_name_format(self):
        """Test for invalid submission in which a listen has a track_name field but it's not a string"""
        with open(self.path_to_data_file('empty_track_name.json'), 'r') as f:
            payload = json.load(f)
            payload["payload"][0]["track_metadata"]["track_name"] = []
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

        payload["payload"][0]["track_metadata"]["track_name"] = 1
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_empty_artist_name(self):
        """ Test for invalid submission in which a listen contains an empty artist name
        """
        with open(self.path_to_data_file('empty_artist_name.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

        del payload["payload"][0]["track_metadata"]["artist_name"]
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_bad_artist_name_format(self):
        """ Test for invalid submission in which a listen has a artist_name field but it's not a string
        """
        with open(self.path_to_data_file('empty_artist_name.json'), 'r') as f:
            payload = json.load(f)
            payload["payload"][0]["track_metadata"]["artist_name"] = None

        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

        payload["payload"][0]["track_metadata"]["artist_name"] = None
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

    def test_missing_track_metadata(self):
        """ Test for invalid submission in which a listen does not contain track_metadata field """
        with open(self.path_to_data_file('invalid_listen_missing_track_metadata.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_null_track_metadata(self):
        """ Test for invalid submission in which a listen has null track_metadata field """
        with open(self.path_to_data_file('invalid_listen_null_track_metadata.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)

    def test_nan_in_json(self):
        """ Test for invalid submission in which a listen has null listened_at field """
        with open(self.path_to_data_file('invalid_listen_nan_in_json.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)

    def test_null_listened_at(self):
        """ Test for invalid submission in which a listen has null listened_at field """
        with open(self.path_to_data_file('invalid_listen_null_listened_at.json'), 'r') as f:
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

    def test_multi_duration(self):
        """ Test for duration and duration_ms both given """
        with open(self.path_to_data_file('multi_duration.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('JSON document should not contain both duration and duration_ms.',
                         response.json['error'])

    def test_invalid_duration(self):
        """ Test for error on invalid duration """
        with open(self.path_to_data_file('invalid_duration.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('Value for duration is invalid, should be a positive integer.',
                         response.json['error'])

        payload["payload"][0]["track_metadata"]["additional_info"]["duration"] = 5345029000
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('Value for duration is too large, max permitted value is 2073600', response.json['error'])

        del payload["payload"][0]["track_metadata"]["additional_info"]["duration"]
        payload["payload"][0]["track_metadata"]["additional_info"]["duration_ms"] = 53450290000
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('Value for duration_ms is too large, max permitted value is 2073600000',
                         response.json['error'])

    def test_valid_duration(self):
        """ Test for valid submission in which a listen contains a valid duration_ms field
            in additional_info
        """
        with open(self.path_to_data_file('valid_duration.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

    def test_string_duration_conversion(self):
        """Test that api converts string durations to integer if possible (but users are discouraged from doing this)"""
        with open(self.path_to_data_file('valid_duration.json'), 'r') as f:
            payload = json.load(f)
        payload["payload"][0]["track_metadata"]["additional_info"]["duration_ms"] = "300000"

        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        url = self.custom_url_for('api_v1.get_listens', user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, 1, query_string={'count': '1'})
        self.assert200(response)
        self.assertEqual(300000,
                         response.json["payload"]["listens"][0]["track_metadata"]["additional_info"]["duration_ms"])

    def test_unicode_null_error(self):
        with open(self.path_to_data_file('listen_having_unicode_null.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['error'], '\x00Fade contains a unicode null')

    def test_additional_info(self):
        """ Test to make sure that user generated data present in additional_info field
            of listens is preserved
        """
        with open(self.path_to_data_file('additional_info.json'), 'r') as f:
            payload = json.load(f)

        payload['payload'][0]['listened_at'] = 1280258690
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        expected_length = 1
        url = self.custom_url_for('api_v1.get_listens',
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

    def test_additional_info_invalid_mbids(self):
        """ Test mbid fields with [], "", null values are dropped without error """
        with open(self.path_to_data_file('invalid_mbid_listens.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        url = self.custom_url_for('api_v1.get_listens', user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, num_items=2, query_string={'count': '2'})
        listens = json.loads(response.data)['payload']['listens']

        additional_info = listens[0]['track_metadata']['additional_info']
        self.assertEqual(["ac4f356f-23e5-40ab-990e-da7e34b65d6e"], additional_info["artist_mbids"])

        additional_info = listens[1]['track_metadata']['additional_info']
        self.assertNotIn("recording_mbid", additional_info)
        self.assertNotIn("artist_mbids", additional_info)
        self.assertNotIn("release_mbid", additional_info)
        self.assertNotIn("work_mbids", additional_info)
        self.assertEqual("2cfad207-3f55-4aec-8120-86cf66e34d59", additional_info["release_group_mbid"])

    def test_similar_users(self):

        response = self.client.get(
            self.custom_url_for('api_v1.get_similar_users', user_name='my_dear_muppet'))
        self.assert404(response)

        with self.db_conn.connection.cursor() as curs:
            data = {self.user2['id']: 0.123}
            curs.execute("""INSERT INTO recommendation.similar_user VALUES (%s, %s)""",
                         (self.user['id'], json.dumps(data)))
        self.db_conn.commit()

        response = self.client.get(
            self.custom_url_for('api_v1.get_similar_users', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data[0]['user_name'], self.user2['musicbrainz_id'])
        self.assertEqual(data[0]['similarity'], 0.123)

        response = self.client.get(self.custom_url_for(
            'api_v1.get_similar_to_user', user_name=self.user['musicbrainz_id'], other_user_name="muppet"))
        self.assert404(response)

        response = self.client.get(self.custom_url_for(
            'api_v1.get_similar_to_user', user_name=self.user['musicbrainz_id'],
            other_user_name=self.user2['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        self.assertEqual(data['user_name'], self.user2['musicbrainz_id'])
        self.assertEqual(data['similarity'], .123)

    def test_latest_import(self):
        """ Test for api.latest_import """

        # initially the value of latest_import will be 0
        response = self.client.get(self.custom_url_for('api_v1.latest_import'), query_string={
            'user_name': self.user['musicbrainz_id']})
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(data['latest_import'], 0)

        # now an update
        val = int(time.time())
        response = self.client.post(
            self.custom_url_for('api_v1.latest_import'),
            data=json.dumps({'ts': val}),
            headers={'Authorization': 'Token {token}'.format(
                token=self.user['auth_token'])}
        )
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # now the value must have changed
        response = self.client.get(self.custom_url_for('api_v1.latest_import'), query_string={
            'user_name': self.user['musicbrainz_id']})
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(data['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(data['latest_import'], val)

    def test_latest_import_unauthorized(self):
        """ Test for invalid tokens passed to user.latest_import view"""

        val = int(time.time())
        response = self.client.post(
            self.custom_url_for('api_v1.latest_import'),
            data=json.dumps({'ts': val}),
            headers={'Authorization': 'Token thisisinvalid'}
        )
        self.assert401(response)
        self.assertEqual(response.json['code'], 401)

    def test_latest_import_unknown_user(self):
        """Tests api.latest_import without a valid username"""
        response = self.client.get(
            self.custom_url_for('api_v1.latest_import'), query_string={'user_name': ''})
        self.assert404(response)
        self.assertEqual(response.json['code'], 404)

    def test_multiple_artist_names(self):
        """ Tests multiple artist names in artist_name field of data """

        with open(self.path_to_data_file('artist_name_list.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('track_metadata.artist_name must be a single string.',
                         response.json['error'])

    def test_too_high_timestamps(self):
        """ Tests for timestamps greater than current time """

        with open(self.path_to_data_file('timestamp_in_ns.json'), 'r') as f:
            payload = json.load(f)
        payload['listened_at'] = int(time.time()) * 10 ** 9
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(
            'Value for key listened_at is too high.', response.json['error'])

    def test_too_low_timestamps(self):
        """ Tests for timestamps earlier than last.fm founding year """
        with open(self.path_to_data_file('timestamp_before_lfm_founding.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual('Value for key listened_at is too low. listened_at timestamp should be'
                         ' greater than 1033410600 (2002-10-01 00:00:00 UTC).', response.json['error'])

    def test_invalid_token_validation(self):
        """Sends an invalid token to api.validate_token"""
        url = self.custom_url_for('api_v1.validate_token')
        response = self.client.get(url, query_string={"token": "invalidtoken"})
        self.assert200(response)
        self.assertEqual(response.json['code'], 200)
        self.assertEqual('Token invalid.', response.json['message'])
        self.assertFalse(response.json['valid'])
        self.assertNotIn('user_name', response.json)

    def test_valid_token_validation(self):
        """Sends a valid token to api.validate_token"""
        url = self.custom_url_for('api_v1.validate_token')
        response = self.client.get(
            url, query_string={"token": self.user['auth_token']})
        self.assert200(response)
        self.assertEqual(response.json['code'], 200)
        self.assertEqual('Token valid.', response.json['message'])
        self.assertTrue(response.json['valid'])
        self.assertEqual(response.json['user_name'],
                         self.user['musicbrainz_id'])

    def test_token_validation_auth_header(self):
        """Sends a valid token to api.validate_token in the Authorization header"""
        url = self.custom_url_for('api_v1.validate_token')
        response = self.client.get(url, headers={
            "Authorization": "Token {}".format(self.user['auth_token'])
        })
        self.assert200(response)
        self.assertEqual(response.json['code'], 200)
        self.assertEqual('Token valid.', response.json['message'])
        self.assertTrue(response.json['valid'])
        self.assertEqual(response.json['user_name'], self.user['musicbrainz_id'])

    def test_get_playing_now(self):
        """ Test for valid submission and retrieval of listen_type 'playing_now'
        """
        r = self.client.get(self.custom_url_for('api_v1.get_playing_now',
                                                user_name='thisuserdoesnotexist'))
        self.assert404(r)

        r = self.client.get(self.custom_url_for('api_v1.get_playing_now',
                                                user_name=self.user['musicbrainz_id']))
        self.assertEqual(r.json['payload']['count'], 0)
        self.assertEqual(len(r.json['payload']['listens']), 0)

        with open(self.path_to_data_file('valid_playing_now.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        r = self.client.get(self.custom_url_for('api_v1.get_playing_now',
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

        url = self.custom_url_for('api_v1.get_listens',
                                  user_name=self.user['musicbrainz_id'])
        response = self.wait_for_query_to_have_items(url, 1)
        data = json.loads(response.data)['payload']
        self.assertEqual(len(data['listens']), 1)

        delete_listen_url = self.custom_url_for('api_v1.delete_listen')
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
        delete_listen_url = self.custom_url_for('api_v1.delete_listen')
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
        delete_listen_url = self.custom_url_for('api_v1.delete_listen')

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
        delete_listen_url = self.custom_url_for('api_v1.delete_listen')

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
        r = self.client.post(self.follow_user_url, headers=self.follow_user_headers)
        self.assert200(r)

        r = self.client.get(
            self.custom_url_for("social_api_v1.get_followers", user_name=self.followed_user["musicbrainz_id"]))
        self.assert200(r)
        self.assertListEqual([self.user["musicbrainz_id"]], r.json['followers'])

    def test_following_returns_the_people_who_follow_the_user(self):
        r = self.client.post(self.follow_user_url, headers=self.follow_user_headers)
        self.assert200(r)

        r = self.client.get(self.custom_url_for("social_api_v1.get_following", user_name=self.user["musicbrainz_id"]))
        self.assert200(r)
        self.assertListEqual(['followed_user'], r.json['following'])

    def test_follow_user(self):
        r = self.client.post(self.follow_user_url, headers=self.follow_user_headers)
        self.assert200(r)
        self.assertTrue(db_user_relationship.is_following_user(self.db_conn, self.user["id"], self.followed_user['id']))

    def test_follow_user_requires_login(self):
        r = self.client.post(self.follow_user_url)
        self.assert401(r)

    def test_following_a_nonexistent_user_errors_out(self):
        r = self.client.post(self.custom_url_for("social_api_v1.follow_user", user_name="user_doesnt_exist_lol"),
                             headers=self.follow_user_headers)
        self.assert404(r)

    def test_following_yourself_errors_out(self):
        r = self.client.post(self.custom_url_for("social_api_v1.follow_user", user_name=self.user["musicbrainz_id"]),
                             headers=self.follow_user_headers)
        self.assert400(r)

    def test_follow_user_twice_leads_to_error(self):
        r = self.client.post(self.follow_user_url, headers=self.follow_user_headers)
        self.assert200(r)
        self.assertTrue(db_user_relationship.is_following_user(self.db_conn, self.user["id"], self.followed_user['id']))

        # now, try to follow again, this time expecting a 400
        r = self.client.post(self.follow_user_url, headers=self.follow_user_headers)
        self.assert400(r)

    def test_unfollow_user(self):
        # first, follow the user
        r = self.client.post(self.follow_user_url, headers=self.follow_user_headers)
        self.assert200(r)
        self.assertTrue(db_user_relationship.is_following_user(self.db_conn, self.user["id"], self.followed_user['id']))

        # now, unfollow and check the db
        r = self.client.post(
            self.custom_url_for("social_api_v1.unfollow_user", user_name=self.followed_user["musicbrainz_id"]),
            headers=self.follow_user_headers
        )
        self.assert200(r)
        self.assertFalse(
            db_user_relationship.is_following_user(
                self.db_conn,
                self.user["id"],
                self.followed_user['id']
            )
        )

    def test_unfollow_not_following_user(self):
        r = self.client.post(
            self.custom_url_for("social_api_v1.unfollow_user", user_name=self.followed_user["musicbrainz_id"]),
            headers=self.follow_user_headers)
        self.assert200(r)
        self.assertFalse(
            db_user_relationship.is_following_user(
                self.db_conn,
                self.user["id"],
                self.followed_user['id']
            )
        )

    def test_unfollow_user_requires_login(self):
        r = self.client.post(
            self.custom_url_for("social_api_v1.unfollow_user", user_name=self.followed_user["musicbrainz_id"]))
        self.assert401(r)

    def test_get_user_services(self):
        db_oauth.save_token(
            self.db_conn,
            user_id=self.user['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        response = self.client.get(
            self.custom_url_for("api_v1.get_service_details", user_name=self.user["musicbrainz_id"]),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(
            {"services": ["spotify"], "user_name": self.user["musicbrainz_id"]},
            response.json
        )

        response = self.client.get(
            self.custom_url_for("api_v1.get_service_details", user_name=self.user["musicbrainz_id"]),
            content_type="application/json"
        )
        self.assert401(response)

        response = self.client.get(
            self.custom_url_for("api_v1.get_service_details", user_name=self.followed_user["musicbrainz_id"]),
            headers={"Authorization": f"Token {self.user['auth_token']}"},
            content_type="application/json"
        )
        self.assert403(response)

    def test_user_recommendations(self):
        r = self.client.get(
            self.custom_url_for("api_v1.user_recommendations", playlist_user_name=self.followed_user["musicbrainz_id"]))
        self.assert200(r)

        r = self.client.get(self.custom_url_for("api_v1.user_recommendations", playlist_user_name="does not exist"))
        self.assert404(r)
