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
from data.model.user_timeline_event import UserTimelineEventType, RecordingRecommendationMetadata
from unittest import mock

import listenbrainz.db.user as db_user
import listenbrainz.db.user_timeline_event as db_user_timeline_event
import listenbrainz.db.user_relationship as db_user_relationship
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
        # see test_unhide_events_for_database_exception for details on this
        self.app.config["TESTING"] = False

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
            url_for('user_timeline_event_api_bp.create_user_notification_event',
            user_name=self.user['musicbrainz_id']),
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
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
            user_name=new_user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata_rec}),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])},
        )
        # Deleting notification
        r_del_not = self.client.post(
            url_for('user_timeline_event_api_bp.delete_feed_events',
            user_name=self.user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.NOTIFICATION.value, 'id': 1}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert200(r_del_not)

        # Checking if notification still exists
        r_not = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed',
            user_name=self.user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        payload_not = r_not.json["payload"]
        self.assertEqual(0, payload_not["count"])
        self.assertEqual(self.user["musicbrainz_id"], payload_not["user_id"])

        # Deleting recommendation event
        r_del_rec = self.client.post(
            url_for('user_timeline_event_api_bp.delete_feed_events',
            user_name=new_user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.RECORDING_RECOMMENDATION.value, 'id': 2}),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])}
        )
        self.assert200(r_del_rec)

        # Checking if recording recommendation still exists
        r_rec = self.client.get(
            url_for('user_timeline_event_api_bp.user_feed',
            user_name=new_user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])}
        )
        payload_rec = r_rec.json["payload"]
        self.assertEqual(0, payload_rec["count"])
        self.assertEqual(new_user["musicbrainz_id"], payload_rec["user_id"])

    def test_delete_feed_events_token_for_authorization(self):
        # Adding notification to the db
        metadata_not = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(11, "troi-bot")
        self.client.post(
            url_for('user_timeline_event_api_bp.create_user_notification_event',
            user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata_not}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        # Attempt to delete notifications by passing no Auth header
        r_not = self.client.post(
            url_for('user_timeline_event_api_bp.delete_feed_events',
            user_name=self.user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.NOTIFICATION.value, 'id': 1}),
        )
        self.assert401(r_not)
        # Adding recording recommendation to db
        new_user = db_user.get_or_create(2, "riksucks")
        metadata_rec = {
            'artist_name': 'Nujabes',
            'track_name': 'Aruarian Dance',
            'artist_msid':  str(uuid.uuid4()),
            'recording_msid': str(uuid.uuid4()),
        }
        self.client.post(
            url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
            user_name=new_user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata_rec}),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])},
        )
        # Deleting recommendation event
        r_rec = self.client.post(
            url_for('user_timeline_event_api_bp.delete_feed_events',
            user_name=new_user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.RECORDING_RECOMMENDATION.value, 'id': 2}),
            headers={'Authorization': 'Token l33thaxors'}
        )
        self.assert401(r_rec)

    @mock.patch("listenbrainz.db.user_timeline_event.delete_user_timeline_event",
        side_effect=DatabaseException)
    def test_delete_feed_events_for_db_exceptions(self, mock_create_event):
        # see test_unhide_events_for_database_exception for details on this
        self.app.config["TESTING"] = False

        # Adding notification to the db
        metadata_not = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(11, "troi-bot")
        self.client.post(
            url_for('user_timeline_event_api_bp.create_user_notification_event',
            user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata_not}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        # Attempt to delete notification
        r = self.client.post(
            url_for('user_timeline_event_api_bp.delete_feed_events',
            user_name=self.user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.NOTIFICATION.value, 'id': 1}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert500(r)
        data = json.loads(r.data)
        self.assertEqual('Something went wrong. Please try again', data['error'])

    def test_delete_feed_events_for_bad_request(self):
        # Adding notification to the db
        metadata_not = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(11, "troi-bot")
        self.client.post(
            url_for('user_timeline_event_api_bp.create_user_notification_event',
            user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata_not}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        # Attempt to delete notification with empty JSON, should throw bad request error
        r = self.client.post(
            url_for('user_timeline_event_api_bp.delete_feed_events',
            user_name=self.user["musicbrainz_id"]),
            data=json.dumps({}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert400(r)

    def test_hide_events(self):
        # creating a new user
        new_user = db_user.get_or_create(2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # user starts following riksucks
        db_user_relationship.insert(self.user['id'], new_user['id'], 'follow')

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.hide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({
                "event_type": event_rec.event_type.value,
                "event_id": event_rec.id
                }
            ),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert200(r)

    def test_hide_events_tokens_for_authorization(self):
        # creating a new user
        new_user = db_user.get_or_create(2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # user starts following riksucks
        db_user_relationship.insert(self.user['id'], new_user['id'], 'follow')

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.hide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({
                "event_type": event_rec.event_type.value,
                "event_id": event_rec.id
                }
            ),
        )
        self.assert401(r)

    def test_hide_events_for_non_followed_users(self):
        # creating a new user
        new_user = db_user.get_or_create(2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.hide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({
                "event_type": event_rec.event_type.value,
                "event_id": event_rec.id
                }
            ),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert401(r)

    @mock.patch(
        "listenbrainz.db.user_timeline_event.hide_user_timeline_event",
        side_effect=DatabaseException
        )
    def test_hide_events_for_database_exception(self, mock_create_event):
        # see test_unhide_events_for_database_exception for details on this
        self.app.config["TESTING"] = False

        # creating a new user
        new_user = db_user.get_or_create(2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # user starts following riksucks
        db_user_relationship.insert(self.user['id'], new_user['id'], 'follow')

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.hide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({
                "event_type": event_rec.event_type.value,
                "event_id": event_rec.id
                }
            ),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert500(r)

    def test_hide_events_for_bad_request(self):
        # creating a new user
        new_user = db_user.get_or_create(2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # user starts following riksucks
        db_user_relationship.insert(self.user['id'], new_user['id'], 'follow')

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.hide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert400(r)

    def test_unhide_events(self):
        # add dummy event
        db_user_timeline_event.hide_user_timeline_event(
            self.user['id'],
            UserTimelineEventType.RECORDING_RECOMMENDATION.value,
            1
        )

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.unhide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({
                "event_type": UserTimelineEventType.RECORDING_RECOMMENDATION.value,
                "event_id": 1
            }),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert200(r)

    def test_unhide_events_for_authorization(self):
        # add dummy event
        db_user_timeline_event.hide_user_timeline_event(
            self.user['id'],
            UserTimelineEventType.RECORDING_RECOMMENDATION.value,
            1
        )

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.unhide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({
                "event_type": UserTimelineEventType.RECORDING_RECOMMENDATION.value,
                "event_id": 1
            }),
        )
        self.assert401(r)

    def test_unhide_events_for_bad_request(self):
        # add dummy event
        db_user_timeline_event.hide_user_timeline_event(
            self.user['id'],
            UserTimelineEventType.RECORDING_RECOMMENDATION.value,
            1
        )

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.unhide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert400(r)

    @mock.patch(
        "listenbrainz.db.user_timeline_event.unhide_timeline_event",
        side_effect=DatabaseException
        )
    def test_unhide_events_for_database_exception(self, mock_create_event):
        # in prod, we have registered error handlers to return 500 response
        # on all uncaught exceptions. if TESTING is set to True, flask will
        # behave differently and instead make the exception visible here rather
        # than a 500 response. also, app is created for each test so don't worry
        # to reset it after the test. similarly, set TESTING to true to help in
        # debugging tests if needed.
        self.app.config["TESTING"] = False

        # add dummy event
        db_user_timeline_event.hide_user_timeline_event(
            self.user['id'],
            UserTimelineEventType.RECORDING_RECOMMENDATION.value,
            1
        )

        # send request to hide event
        r = self.client.post(
            url_for(
                'user_timeline_event_api_bp.unhide_user_timeline_event',
                user_name=self.user['musicbrainz_id']
            ),
            data=json.dumps({
                "event_type": UserTimelineEventType.RECORDING_RECOMMENDATION.value,
                "event_id": 1
            }),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert500(r)
