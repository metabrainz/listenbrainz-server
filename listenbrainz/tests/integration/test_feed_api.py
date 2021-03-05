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

from data.model.user_timeline_event import UserTimelineEventMetadata
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from flask import url_for, current_app

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import listenbrainz.db.user_timeline_event as db_user_timeline_event
import time
import json
import uuid


class FeedAPITestCase(ListenAPIIntegrationTestCase):

    def create_and_follow_user(self, user: int, mb_row_id: int, name: str) -> dict:
        following_user = db_user.get_or_create(mb_row_id, name)
        db_user_relationship.insert(user, following_user['id'], 'follow')
        return following_user

    def setUp(self):
        super(FeedAPITestCase, self).setUp()
        self.main_user = db_user.get_or_create(100, 'param')
        self.following_user_1 = self.create_and_follow_user(self.main_user['id'], 102, 'following_1')
        self.following_user_2 = self.create_and_follow_user(self.main_user['id'], 103, 'following_2')

    def test_it_sends_listens_for_users_that_are_being_followed(self):
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        ts = int(time.time())
        # send 3 listens for the following_user_1
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts - i
            response = self.send_data(payload, user=self.following_user_1)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        # send 3 listens with lower timestamps for following_user_2
        for i in range(3):
            payload['payload'][0]['listened_at'] = ts - 10 - i
            response = self.send_data(payload, user=self.following_user_2)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        # This sleep allows for the timescale subscriber to take its time in getting
        # the listen submitted from redis and writing it to timescale.
        time.sleep(2)

        response = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
        )
        self.assert200(response)
        payload = response.json['payload']

        # should only have 4 listens, 2 per user
        self.assertEqual(4, payload['count'])

        # first 2 events should have higher timestamps and user should be following_1
        self.assertEqual('listen', payload['events'][0]['event_type'])
        self.assertEqual(ts, payload['events'][0]['created'])
        self.assertEqual('following_1', payload['events'][0]['user_name'])
        self.assertEqual('listen', payload['events'][1]['event_type'])
        self.assertEqual(ts - 1, payload['events'][1]['created'])
        self.assertEqual('following_1', payload['events'][1]['user_name'])

        # next 2 events should have lower timestamps and user should be following_2
        self.assertEqual('listen', payload['events'][2]['event_type'])
        self.assertEqual(ts - 10, payload['events'][2]['created'])
        self.assertEqual('following_2', payload['events'][2]['user_name'])
        self.assertEqual('listen', payload['events'][3]['event_type'])
        self.assertEqual(ts - 11, payload['events'][3]['created'])
        self.assertEqual('following_2', payload['events'][3]['user_name'])

    def test_it_raises_unauthorized_for_a_different_user(self):
        r = self.client.get('/1/user/someotheruser/feed/events')
        self.assert401(r)

    def test_it_honors_request_parameters(self):
        with open(self.path_to_data_file('valid_single.json'), 'r') as f:
            payload = json.load(f)

        # send a listen per user with timestamp 1, 2, 3
        ts = int(time.time())
        for i in range(1, 4):
            payload['payload'][0]['listened_at'] = ts + i
            response = self.send_data(payload, user=self.following_user_1)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

            response = self.send_data(payload, user=self.following_user_2)
            self.assert200(response)
            self.assertEqual(response.json['status'], 'ok')

        time.sleep(5)

        # max_ts = 2, should have sent back 2 listens
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'max_ts': ts + 2}
        )
        self.assert200(r)
        self.assertEqual(2, r.json['payload']['count'])

        # max_ts = 4, should have sent back 4 listens
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'max_ts': ts + 4}
        )
        self.assert200(r)
        self.assertEqual(4, r.json['payload']['count'])

        # min_ts = 1, should have sent back 4 listens
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'min_ts': ts + 1}
        )
        self.assert200(r)
        self.assertEqual(4, r.json['payload']['count'])

        # min_ts = 2, should have sent back 2 listens
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'min_ts': ts + 2}
        )
        self.assert200(r)
        self.assertEqual(2, r.json['payload']['count'])

        # min_ts = 1, max_ts = 3, should have sent back 2 listens
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'min_ts': ts + 1, 'max_ts': ts + 3}
        )
        self.assert200(r)
        self.assertEqual(2, r.json['payload']['count'])

        # should honor count
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'count': 1}
        )
        self.assert200(r)
        self.assertEqual(1, r.json['payload']['count'])

    def test_it_returns_follow_events(self):
        # make a user you're following follow a new user
        new_user_1 = db_user.get_or_create(104, 'new_user_1')
        db_user_relationship.insert(self.following_user_1['id'], new_user_1['id'], 'follow')


        # this should show up in the events
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'max_ts': int(time.time()) + 1}
        )
        self.assert200(r)
        self.assertEqual(1, r.json['payload']['count'])
        self.assertEqual('follow', r.json['payload']['events'][0]['event_type'])
        self.assertEqual('following_1', r.json['payload']['events'][0]['user_name'])
        self.assertEqual('following_1', r.json['payload']['events'][0]['metadata']['user_name_0'])
        self.assertEqual('new_user_1', r.json['payload']['events'][0]['metadata']['user_name_1'])
        self.assertEqual('follow', r.json['payload']['events'][0]['metadata']['relationship_type'])

    def test_it_returns_recording_recommendation_events(self):
        # create a recording recommendation for a user we follow
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.following_user_1['id'],
            metadata=UserTimelineEventMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )


        # this should show up in the events
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
            query_string={'max_ts': int(time.time()) + 1}
        )
        self.assert200(r)
        self.assertEqual(1, r.json['payload']['count'])
        self.assertEqual('recording_recommendation', r.json['payload']['events'][0]['event_type'])
        self.assertEqual('following_1', r.json['payload']['events'][0]['user_name'])
        self.assertEqual('Sunflower', r.json['payload']['events'][0]['metadata']['track_metadata']['track_name'])
        self.assertEqual('Swae Lee & Post Malone', r.json['payload']['events'][0]['metadata']['track_metadata']['artist_name'])

    def test_it_returns_empty_list_if_user_does_not_follow_anyone(self):
        new_user = db_user.get_or_create(111, 'totally_new_user_with_no_friends')
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=new_user['musicbrainz_id']),
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
        new_user_1 = db_user.get_or_create(104, 'new_user_1')
        db_user_relationship.insert(self.following_user_1['id'], new_user_1['id'], 'follow')

        time.sleep(1.5) # sleep a bit to avoid ordering conflicts, cannot mock this time as it comes from postgres

        # create a recording recommendation for a user we follow
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.following_user_1['id'],
            metadata=UserTimelineEventMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )

        time.sleep(2)

        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.main_user['musicbrainz_id']),
            headers={'Authorization': f"Token {self.main_user['auth_token']}"},
        )
        self.assert200(r)
        self.assertEqual(3, r.json['payload']['count'])
        import pdb; pdb.set_trace()
        self.assertEqual('recording_recommendation', r.json['payload']['events'][0]['event_type'])
        self.assertEqual('follow', r.json['payload']['events'][1]['event_type'])
        self.assertEqual('listen', r.json['payload']['events'][2]['event_type'])
