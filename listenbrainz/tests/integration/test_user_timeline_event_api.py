# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2021 Param Singh <me@param.codes>
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

from flask import url_for, current_app
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from data.model.user_timeline_event import UserTimelineEventType
from unittest import mock

import listenbrainz.db.user as db_user
import listenbrainz.db.user_timeline_event as db_user_timeline_event
import time
import json
import uuid


class UserTimelineAPITestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super(UserTimelineAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'friendly neighborhood spider-man')
        events = db_user_timeline_event.get_user_track_recommendation_events(
            user_id=self.user['id'],
            count=1,
        )
        self.assertListEqual([], events)

    def test_it_writes_an_event_to_the_database(self):

        metadata = {
            'artist_name': 'Kanye West',
            'track_name': 'Fade',
            'artist_msid':  str(uuid.uuid4()),
            'recording_msid': str(uuid.uuid4()),
        }
        r = self.client.post(
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert200(r)

        events = db_user_timeline_event.get_user_track_recommendation_events(
            user_id=self.user['id'],
            count=1,
        )
        self.assertEqual(1, len(events))
        self.assertEqual('Kanye West', events[0].metadata.artist_name)
        self.assertEqual('Fade', events[0].metadata.track_name)

    def test_it_checks_auth_token_for_authorization(self):
        metadata = {
            'artist_name': 'Kanye West',
            'track_name': 'Fade',
            'artist_msid':  str(uuid.uuid4()),
            'recording_msid': str(uuid.uuid4()),
        }

        # send a request without a token
        r = self.client.post(
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
        )
        self.assert401(r)

        # send a request with an incorrect token
        r = self.client.post(
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token plsnohack'},
        )
        self.assert401(r)

        # check that no events were created in the database
        events = db_user_timeline_event.get_user_track_recommendation_events(
            user_id=self.user['id'],
            count=1,
        )
        self.assertListEqual([], events)

    def test_it_validates_metadata_json(self):
        metadata = {}

        # empty metadata should 400
        r = self.client.post(
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert400(r)

    @mock.patch('listenbrainz.db.user_timeline_event.create_user_track_recommendation_event', side_effect=DatabaseException)
    def test_it_handles_database_exceptions(self, mock_create_event):
        metadata = {
            'artist_name': 'Kanye West',
            'track_name': 'Fade',
            'artist_msid':  str(uuid.uuid4()),
            'recording_msid': str(uuid.uuid4()),
        }
        r = self.client.post(
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert500(r)
        data = json.loads(r.data)
        self.assertEqual('Something went wrong, please try again.', data['error'])

    def test_it_raises_error_if_auth_token_and_user_name_do_not_match(self):
        metadata = {
            'artist_name': 'Kanye West',
            'track_name': 'Fade',
            'artist_msid':  str(uuid.uuid4()),
            'recording_msid': str(uuid.uuid4()),
        }
        r = self.client.post(
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event', user_name='notthemainuser'),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert401(r)
        data = json.loads(r.data)
        self.assertEqual("You don't have permissions to post to this user's timeline.", data['error'])

    def test_post_notification_authorization_fails(self):
        metadata = {
            "message": "Testing",
            "link": "http://localhost"
        }
        r = self.client.post(
            url_for('user_timeline_event_api_bp.create_user_notification_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert403(r)
        data = json.loads(r.data)
        self.assertEqual("Only approved users are allowed to post a message on a user's timeline.", data['error'])

    def test_post_notification_success(self):
        metadata = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(11, "troi-bot")
        r = self.client.post(
            url_for('user_timeline_event_api_bp.create_user_notification_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        self.assert200(r)

    def test_get_notification_event(self):
        metadata = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(11, "troi-bot")
        self.client.post(
            url_for('user_timeline_event_api_bp.create_user_notification_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        r = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )

        payload = r.json['payload']
        self.assertEqual(1, payload['count'])
        self.assertEqual(self.user['musicbrainz_id'], payload['user_id'])

        event = payload['events'][0]
        self.assertEqual('notification', event['event_type'])
        self.assertEqual('You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>',
                         event['metadata']['message'])
        self.assertEqual(approved_user['musicbrainz_id'], event['user_name'])

    def test_delete_feed_events(self):
        # Adding notification to the db
        metadata_not = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(11, "troi-bot")
        self.client.post(
            url_for('user_timeline_event_api_bp.create_user_notification_event', user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata_not}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        # Adding recording recommendation to db
        new_user = db_user.get_or_create(2, "riksucks")
        metadata_rec = {
            'artist_name': 'Nujabes',
            'track_name': 'Aruarian Dance',
            'artist_msid':  str(uuid.uuid4()),
            'recording_msid': str(uuid.uuid4()),
        }
        self.client.post(
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event', user_name=new_user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata_rec}),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])},
        )
        # Checking if recording recommendation exists in db or not
        events = db_user_timeline_event.get_user_track_recommendation_events(
            user_id=new_user["id"],
            count=1,
        )
        self.assertEqual(1, len(events))
        self.assertEqual(UserTimelineEventType.RECORDING_RECOMMENDATION, events[0].event_type)

        # Checking if notification exists in db or not
        r_not = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        payload_not = r_not.json["payload"]
        self.assertEqual(1, payload_not["count"])
        self.assertEqual(self.user["musicbrainz_id"], payload_not["user_id"])
        event_not = payload_not["events"][0]
        self.assertEqual(UserTimelineEventType.NOTIFICATION.value, event_not["event_type"])

        # Deleting notification
        self.client.post(
            url_for('user_timeline_event_api_bp.delete_feed_events', user_name=self.user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.NOTIFICATION.value, 'id': event_not["id"]}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        # Checking if notification still exists
        r_not = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=self.user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        payload_not = r_not.json["payload"]
        self.assertEqual(0, payload_not["count"])
        self.assertEqual(self.user["musicbrainz_id"], payload_not["user_id"])

        # Deleting recommendation event
        self.client.post(
            url_for('user_timeline_event_api_bp.delete_feed_events', user_name=new_user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.RECORDING_RECOMMENDATION.value, 'id': events[0].id}),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])}
        )
        # Checking if recording reccomendation still exists
        r_rec = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed', user_name=new_user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])}
        )
        payload_rec = r_rec.json["payload"]
        self.assertEqual(0, payload_rec["count"])
        self.assertEqual(new_user["id"], events[0].user_id)
