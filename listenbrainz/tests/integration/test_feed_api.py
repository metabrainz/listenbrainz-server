# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2020 Param Singh <iliekcomputers@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
from sqlalchemy import text

from listenbrainz import messybrainz
from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.db.model.user_timeline_event import RecordingRecommendationMetadata
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import listenbrainz.db.user_timeline_event as db_user_timeline_event
import time
import json
from listenbrainz.webserver.views.user_timeline_event_api import DEFAULT_LISTEN_EVENT_WINDOW_NEW


class FeedAPITestCase(ListenAPIIntegrationTestCase):

    def insert_metadata(self):
        query = """
            INSERT INTO mapping.mb_metadata_cache
                       (recording_mbid, artist_mbids, release_mbid, recording_data, artist_data, tag_data, release_data, dirty)
                VALUES ('34c208ee-2de7-4d38-b47e-907074866dd3'
                      , '{4a779683-5404-4b90-a0d7-242495158265}'::UUID[]
                      , '1390f1b7-7851-48ae-983d-eb8a48f78048'
                      , '{"name": "52 Bars", "rels": [], "length": 214024}'
                      , '{"name": "Karan Aujla", "artists": [{"area": "Punjab", "name": "Karan Aujla", "rels": {"wikidata": "https://www.wikidata.org/wiki/Q58008320", "social network": "https://www.instagram.com/karanaujla_official/"}, "type": "Person", "gender": "Male", "begin_year": 1997, "join_phrase": ""}], "artist_credit_id": 2892477}'
                      , '{"artist": [], "recording": [], "release_group": []}'
                      , '{"mbid": "1390f1b7-7851-48ae-983d-eb8a48f78048", "name": "Four You", "year": 2023, "caa_id": 34792503592, "caa_release_mbid": "1390f1b7-7851-48ae-983d-eb8a48f78048", "album_artist_name": "Karan Aujla", "release_group_mbid": "eb8734c9-127d-495e-b908-9194cdbac45d"}'
                      , 'f'
                       )
        """
        self.ts_conn.execute(text(query))
        msid = messybrainz.submit_recording(self.ts_conn, "Strangers", "Portishead", "Dummy", None, 291160)
        self.ts_conn.commit()
        return msid

    def create_and_follow_user(self, user: int, mb_row_id: int, name: str) -> dict:
        following_user = db_user.get_or_create(self.db_conn, mb_row_id, name)
        db_user_relationship.insert(self.db_conn, user, following_user['id'], 'follow')
        return following_user

    def create_similar_user(self, similar_to_user: int, mb_row_id: int, similarity: float, name: str) -> dict:
        similar_user = db_user.get_or_create(self.db_conn, mb_row_id, name)
        self.similar_user_data[similar_user['id']] = similarity
        self.db_conn.execute(text("""
            INSERT INTO recommendation.similar_user (user_id, similar_users)
                 VALUES (:similar_to_user, :similar_users)
            ON CONFLICT (user_id)
              DO UPDATE
                    SET similar_users = EXCLUDED.similar_users
            """), {
            "similar_to_user": similar_to_user,
            "similar_users": json.dumps(self.similar_user_data)
        })
        self.db_conn.commit()
        return similar_user

    def remove_own_follow_events(self, payload: dict) -> dict:
        new_events = []
        for event in payload['events']:
            if event['event_type'] == 'follow' and event['user_name'] == self.main_user['musicbrainz_id']:
                continue
            new_events.append(event)
        payload['events'] = new_events
        payload['count'] = len(new_events)
        return payload

    def setUp(self):
        super(FeedAPITestCase, self).setUp()
        self.main_user = db_user.get_or_create(self.db_conn, 100, 'param')
        self.following_user_1 = self.create_and_follow_user(self.main_user['id'], 102, 'following_1')
        self.following_user_2 = self.create_and_follow_user(self.main_user['id'], 103, 'following_2')


    def test_it_sends_all_listens_for_users_that_are_similar(self):
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        self.similar_user_data = dict()
        similar_user_1 = self.create_similar_user(self.main_user['id'], 104, 0.1, 'similar_1')
        similar_user_2 = self.create_similar_user(self.main_user['id'], 105, 0.2, 'similar_2')

        ts = int(time.time())
        # Send 3 listens for the following_user_1
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts - i
            response = self.send_data(payload, user=similar_user_1)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        # Send 3 listens with lower timestamps for similar_user_2
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts - 10 - i
            response = self.send_data(payload, user=similar_user_2)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        from datetime import timedelta
        listenWindowMillisec = int(DEFAULT_LISTEN_EVENT_WINDOW_NEW / timedelta(seconds=1))

        # Sending a listen with time difference slightly lesser than DEFAULT_LISTEN_EVENT_WINDOW_NEW
        payload['payload'][0]['listened_at'] = ts - listenWindowMillisec + 1000
        response = self.send_data(payload, user=similar_user_1)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # Sending a listen with time difference slightly greater than DEFAULT_LISTEN_EVENT_WINDOW_NEW
        payload['payload'][0]['listened_at'] = ts - listenWindowMillisec - 1000
        response = self.send_data(payload, user=similar_user_2)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # This sleep allows for the timescale subscriber to take its time in getting
        # the listen submitted from redis and writing it to timescale.
        time.sleep(2)

        response = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed_listens_similar',
                                user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
        )
        self.assert200(response)
        payload = response.json['payload']

        # should have 7 listens only. As one listen is out of seach interval, it should not be in payload.
        self.assertEqual(7, payload['count'])

        # first 3 events should have higher timestamps and user should be similar_1
        self.assertEqual('listen', payload['events'][0]['event_type'])
        self.assertEqual(ts, payload['events'][0]['created'])
        self.assertEqual('similar_1', payload['events'][0]['user_name'])
        self.assertEqual(0.1, payload['events'][0]['similarity'])

        self.assertEqual('listen', payload['events'][1]['event_type'])
        self.assertEqual(ts - 1, payload['events'][1]['created'])
        self.assertEqual('similar_1', payload['events'][1]['user_name'])
        self.assertEqual(0.1, payload['events'][1]['similarity'])

        self.assertEqual('listen', payload['events'][2]['event_type'])
        self.assertEqual(ts - 2, payload['events'][2]['created'])
        self.assertEqual('similar_1', payload['events'][2]['user_name'])
        self.assertEqual(0.1, payload['events'][2]['similarity'])

        # next 3 events should have lower timestamps and user should be similar_2
        self.assertEqual('listen', payload['events'][3]['event_type'])
        self.assertEqual(ts - 10, payload['events'][3]['created'])
        self.assertEqual('similar_2', payload['events'][3]['user_name'])
        self.assertEqual(0.2, payload['events'][3]['similarity'])

        self.assertEqual('listen', payload['events'][4]['event_type'])
        self.assertEqual(ts - 11, payload['events'][4]['created'])
        self.assertEqual('similar_2', payload['events'][4]['user_name'])
        self.assertEqual(0.2, payload['events'][4]['similarity'])

        self.assertEqual('listen', payload['events'][5]['event_type'])
        self.assertEqual(ts - 12, payload['events'][5]['created'])
        self.assertEqual('similar_2', payload['events'][5]['user_name'])
        self.assertEqual(0.2, payload['events'][5]['similarity'])

    def test_it_sends_all_listens_for_users_that_are_being_followed(self):
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        ts = int(time.time())
        # Send 3 listens for the following_user_1
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts - i
            response = self.send_data(payload, user=self.following_user_1)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        # Send 3 listens with lower timestamps for following_user_2
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts - 10 - i
            response = self.send_data(payload, user=self.following_user_2)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        from datetime import timedelta
        listenWindowMillisec = int(DEFAULT_LISTEN_EVENT_WINDOW_NEW / timedelta(seconds=1))

        # Sending a listen with time difference slightly lesser than DEFAULT_LISTEN_EVENT_WINDOW_NEW
        payload['payload'][0]['listened_at'] = ts - listenWindowMillisec + 1000
        response = self.send_data(payload, user=self.following_user_1)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # Sending a listen with time difference slightly greater than DEFAULT_LISTEN_EVENT_WINDOW_NEW
        payload['payload'][0]['listened_at'] = ts - listenWindowMillisec - 1000
        response = self.send_data(payload, user=self.following_user_1)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # This sleep allows for the timescale subscriber to take its time in getting
        # the listen submitted from redis and writing it to timescale.
        time.sleep(2)

        response = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed_listens_following',
                                user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
        )
        self.assert200(response)
        payload = response.json['payload']

        # the payload contains events for the users we've followed, but we don't care about those
        # for now, so let's remove them for this test.
        payload = self.remove_own_follow_events(payload)

        # should have 7 listens only. As one listen is out of seach interval, it should not be in payload.
        self.assertEqual(7, payload['count'])

        # first 3 events should have higher timestamps and user should be following_1
        self.assertEqual('listen', payload['events'][0]['event_type'])
        self.assertEqual(ts, payload['events'][0]['created'])
        self.assertEqual('following_1', payload['events'][0]['user_name'])
        self.assertEqual('listen', payload['events'][1]['event_type'])
        self.assertEqual(ts - 1, payload['events'][1]['created'])
        self.assertEqual('following_1', payload['events'][1]['user_name'])
        self.assertEqual('listen', payload['events'][2]['event_type'])
        self.assertEqual(ts - 2, payload['events'][2]['created'])
        self.assertEqual('following_1', payload['events'][2]['user_name'])

        # next 3 events should have lower timestamps and user should be following_2
        self.assertEqual('listen', payload['events'][3]['event_type'])
        self.assertEqual(ts - 10, payload['events'][3]['created'])
        self.assertEqual('following_2', payload['events'][3]['user_name'])
        self.assertEqual('listen', payload['events'][4]['event_type'])
        self.assertEqual(ts - 11, payload['events'][4]['created'])
        self.assertEqual('following_2', payload['events'][4]['user_name'])
        self.assertEqual('listen', payload['events'][5]['event_type'])
        self.assertEqual(ts - 12, payload['events'][5]['created'])
        self.assertEqual('following_2', payload['events'][5]['user_name'])

    def test_it_raises_unauthorized_for_a_different_user(self):
        r = self.client.get('/1/user/someotheruser/feed/events')
        self.assert401(r)

    def test_it_honors_request_parameters(self):

        msid = self.insert_metadata()
        # send a recommendation event at different timestamps
        ts = int(time.time())
        for i in range(1, 4):
            # create a recording recommendation for users we follow
            db_user_timeline_event.create_user_track_recommendation_event(
                self.db_conn,
                user_id=self.following_user_1["id"],
                metadata=RecordingRecommendationMetadata(
                    recording_mbid="34c208ee-2de7-4d38-b47e-907074866dd3",
                    recording_msid=msid
                ),
            )
            # Sleep after each insert because we can't set a specific timestamp
            time.sleep(2)

        r = self.client.get(
            self.custom_url_for(
                "user_timeline_event_api_bp.user_feed",
                user_name=self.main_user["musicbrainz_id"],
            ),
            headers={"Authorization": f"Token {self.main_user['auth_token']}"},
        )
        payload = self.remove_own_follow_events(r.json["payload"])
        # max_ts = +1, should have sent back 1 event
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'max_ts': ts+1}
        )
        self.assert200(r)
        # the payload contains events for the users we've followed, but we don't care about those
        # for now, so let's remove them for this test.
        payload = self.remove_own_follow_events(r.json['payload'])
        self.assertEqual(1, payload['count'])

        # max_ts = +3, should have sent back 2 events
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'max_ts': ts + 3}
        )
        self.assert200(r)
        payload = self.remove_own_follow_events(r.json['payload'])
        self.assertEqual(2, payload['count'])

        # min_ts = ts, should have sent back 3 events
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'min_ts': ts}
        )
        self.assert200(r)
        payload = self.remove_own_follow_events(r.json['payload'])
        self.assertEqual(3, payload['count'])

        # min_ts = +2, should have sent back 2 events
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'min_ts': ts + 2}
        )
        self.assert200(r)
        payload = self.remove_own_follow_events(r.json['payload'])
        self.assertEqual(2, payload['count'])

        # min_ts = 1, max_ts = 3, should have sent back 1 events
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'min_ts': ts + 1, 'max_ts': ts + 3}
        )
        self.assert200(r)
        payload = self.remove_own_follow_events(r.json['payload'])
        self.assertEqual(1, payload['count'])

        # should honor count
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'count': 1}
        )
        self.assert200(r)
        self.assertEqual(1, r.json['payload']['count'])

    def test_it_returns_follow_events(self):
        # make a user you're following follow a new user
        new_user_1 = db_user.get_or_create(self.db_conn, 104, 'new_user_1')
        db_user_relationship.insert(self.db_conn, self.following_user_1['id'], new_user_1['id'], 'follow')

        # this should show up in the events
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'max_ts': int(time.time()) + 1}
        )
        self.assert200(r)

        # should contain 3 events, the main user followed 2 people and then we created a new follow event
        self.assertEqual(3, r.json['payload']['count'])

        # the first event should be the latest one
        self.assertEqual('follow', r.json['payload']['events'][0]['event_type'])
        self.assertEqual('following_1', r.json['payload']['events'][0]['user_name'])
        self.assertEqual('following_1', r.json['payload']['events'][0]['metadata']['user_name_0'])
        self.assertEqual('new_user_1', r.json['payload']['events'][0]['metadata']['user_name_1'])
        self.assertEqual('follow', r.json['payload']['events'][0]['metadata']['relationship_type'])

        # now, check the main user's own following events
        self.assertEqual('follow', r.json['payload']['events'][1]['event_type'])
        self.assertEqual(self.main_user['musicbrainz_id'], r.json['payload']['events'][1]['user_name'])
        self.assertEqual(self.main_user['musicbrainz_id'], r.json['payload']['events'][1]['metadata']['user_name_0'])
        self.assertEqual(self.following_user_2['musicbrainz_id'],
                         r.json['payload']['events'][1]['metadata']['user_name_1'])
        self.assertEqual('follow', r.json['payload']['events'][1]['metadata']['relationship_type'])

        self.assertEqual('follow', r.json['payload']['events'][2]['event_type'])
        self.assertEqual(self.main_user['musicbrainz_id'], r.json['payload']['events'][2]['user_name'])
        self.assertEqual(self.main_user['musicbrainz_id'], r.json['payload']['events'][2]['metadata']['user_name_0'])
        self.assertEqual(self.following_user_1['musicbrainz_id'],
                         r.json['payload']['events'][2]['metadata']['user_name_1'])
        self.assertEqual('follow', r.json['payload']['events'][2]['metadata']['relationship_type'])

    def test_it_returns_recording_recommendation_events(self):
        msid = self.insert_metadata()
        # create a recording recommendation ourselves
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.main_user['id'],
            metadata=RecordingRecommendationMetadata(recording_msid=msid)
        )

        # create a recording recommendation for a user we follow
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.following_user_1['id'],
            metadata=RecordingRecommendationMetadata(recording_mbid="34c208ee-2de7-4d38-b47e-907074866dd3")
        )

        # this should show up in the events
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'max_ts': int(time.time()) + 1}
        )
        self.assert200(r)

        # first, let's remove the own follow events, we don't care about those in this test.
        payload = self.remove_own_follow_events(r.json['payload'])

        # now, check for both the recording recommendations and their order
        self.assertEqual(2, payload['count'])
        self.assertEqual('recording_recommendation', payload['events'][0]['event_type'])
        self.assertEqual('following_1', payload['events'][0]['user_name'])
        self.assertEqual({
            'additional_info': None,
            'artist_name': 'Karan Aujla',
            'mbid_mapping': {
                'artist_mbids': ['4a779683-5404-4b90-a0d7-242495158265'],
                'artists': [
                    {
                        'artist_credit_name': 'Karan Aujla',
                        'artist_mbid': '4a779683-5404-4b90-a0d7-242495158265',
                        'join_phrase': ''
                    }
                ],
                'caa_id': 34792503592,
                'caa_release_mbid': '1390f1b7-7851-48ae-983d-eb8a48f78048',
                'recording_mbid': '34c208ee-2de7-4d38-b47e-907074866dd3',
                'release_mbid': '1390f1b7-7851-48ae-983d-eb8a48f78048'
            },
            'release_name': 'Four You',
            'track_name': '52 Bars'
        }, payload['events'][0]['metadata']['track_metadata'])

        self.assertEqual('recording_recommendation', payload['events'][1]['event_type'])
        self.assertEqual(self.main_user['musicbrainz_id'], payload['events'][1]['user_name'])
        self.assertEqual('Portishead', payload['events'][1]['metadata']['track_metadata']['artist_name'])
        self.assertEqual('Strangers', payload['events'][1]['metadata']['track_metadata']['track_name'])
        self.assertEqual('Dummy', payload['events'][1]['metadata']['track_metadata']['release_name'])
        self.assertEqual(msid, payload['events'][1]['metadata']['track_metadata']['additional_info']['recording_msid'])

    def test_it_returns_empty_list_if_user_does_not_follow_anyone(self):
        new_user = db_user.get_or_create(self.db_conn, 111, 'totally_new_user_with_no_friends')
        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=new_user['musicbrainz_id']),
            headers={'Authorization': f"Token {new_user['auth_token']}"},
        )
        self.assert200(r)
        self.assertListEqual([], r.json['payload']['events'])

    def test_it_returns_all_types_of_events_sorted_by_time_in_descending_order(self):
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send a listen from the past
        ts = int(time.time())
        payload['payload'][0]['listened_at'] = ts - 10
        response = self.send_data(payload, user=self.following_user_1)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # make a user you're following follow a new user
        new_user_1 = db_user.get_or_create(self.db_conn, 104, 'new_user_1')
        db_user_relationship.insert(self.db_conn, self.following_user_1['id'], new_user_1['id'], 'follow')

        time.sleep(1)  # sleep a bit to avoid ordering conflicts, cannot mock this time as it comes from postgres
        self.insert_metadata()

        # create a recording recommendation for a user we follow
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.following_user_1['id'],
            metadata=RecordingRecommendationMetadata(recording_mbid="34c208ee-2de7-4d38-b47e-907074866dd3")
        )

        time.sleep(1)

        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
        )
        self.assert200(r)
        self.assertEqual(4, r.json['payload']['count'])  # 3 events we created + 2 own follow events
        self.assertEqual('recording_recommendation', r.json['payload']['events'][0]['event_type'])
        self.assertEqual('follow', r.json['payload']['events'][1]['event_type'])
