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

from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService, CRITIQUEBRAINZ_REVIEW_SUBMIT_URL, \
    CRITIQUEBRAINZ_REVIEW_FETCH_URL
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.db.model.user_timeline_event import UserTimelineEventType, RecordingRecommendationMetadata
from unittest import mock

import requests_mock

import listenbrainz.db.user as db_user
import listenbrainz.db.user_timeline_event as db_user_timeline_event
import listenbrainz.db.user_relationship as db_user_relationship
import time
import json
import uuid


class UserTimelineAPITestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super(UserTimelineAPITestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 199, 'friendly neighborhood spider-man')
        with self.app.app_context():
            CritiqueBrainzService().add_new_user(self.user['id'], {
                "access_token": "foobar",
                "refresh_token": "foobar",
                "expires_in": 3600
            })
        self.review_metadata = {
            "entity_name": "Heart Shaker",
            "entity_id": str(uuid.uuid4()),
            "entity_type": "recording",
            "rating": 5,
            "language": "en",
            "text": "Review text goes here ...",
        }
        # by default this is True, we set to False so that the Flask handler to automatically
        # catch uncaught exceptions works and wraps those in a 500.
        self.app.config["TESTING"] = False

    def test_recommendation_writes_an_event_to_the_database(self):
        metadata = {'recording_msid': str(uuid.uuid4())}
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert200(r)

        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=[self.user['id']],
            min_ts=0,
            max_ts=int(time.time()) + 1000,
            count=1,
        )
        self.assertEqual(1, len(events))
        self.assertEqual(metadata["recording_msid"], events[0].metadata.recording_msid)

    def test_recommendation_mbid_only(self):
        """ Test recommendation with mbid only works """
        metadata = {'recording_mbid': str(uuid.uuid4())}
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert200(r)

        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=[self.user['id']],
            min_ts=0,
            max_ts=int(time.time()) + 1000,
            count=1,
        )
        self.assertEqual(1, len(events))
        self.assertEqual(metadata['recording_mbid'], events[0].metadata.recording_mbid)

    def test_recommendation_checks_auth_token_for_authorization(self):
        metadata = {
            'artist_name': 'Kanye West',
            'track_name': 'Fade',
            'recording_msid': str(uuid.uuid4()),
        }

        # send a request without a token
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
        )
        self.assert401(r)

        # send a request with an incorrect token
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token plsnohack'},
        )
        self.assert401(r)

        # check that no events were created in the database
        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=[self.user['id']],
            min_ts=0,
            max_ts=int(time.time()) + 1000,
            count=1,
        )
        self.assertListEqual([], events)

    def test_recommendation_validates_metadata_json(self):
        metadata = {}

        # empty metadata should 400
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert400(r)

    @mock.patch('listenbrainz.db.user_timeline_event.create_user_track_recommendation_event',
                side_effect=DatabaseException)
    def test_recommendation_handles_database_exceptions(self, mock_create_event):
        # see test_unhide_events_for_database_exception for details on this
        self.app.config["TESTING"] = False
        metadata = {
            'artist_name': 'Kanye West',
            'track_name': 'Fade',
            'recording_msid': str(uuid.uuid4()),
        }
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
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
            'recording_msid': str(uuid.uuid4()),
        }
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name='notthemainuser'),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert403(r)
        data = json.loads(r.data)
        self.assertEqual("You don't have permissions to post to this user's timeline.", data['error'])

    def test_post_notification_authorization_fails(self):
        metadata = {
            "message": "Testing",
            "link": "http://localhost"
        }
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_notification_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert403(r)
        data = json.loads(r.data)
        self.assertEqual("Only approved users are allowed to post a message on a user's timeline.", data['error'])

    def test_post_notification_success(self):
        metadata = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(self.db_conn, 11, "troi-bot")
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_notification_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        self.assert200(r)

    def test_get_notification_event(self):
        metadata = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(self.db_conn, 11, "troi-bot")
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_notification_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        self.assert200(r)
        time.sleep(1)

        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert200(r)
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
        approved_user = db_user.get_or_create(self.db_conn, 11, "troi-bot")
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_notification_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata_not}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        self.assert200(r)
        notification_event_id = r.json["id"]
        # Adding recording recommendation to db
        new_user = db_user.get_or_create(self.db_conn, 202, "riksucks")
        metadata_rec = {
            'artist_name': 'Nujabes',
            'track_name': 'Aruarian Dance',
            'recording_msid': str(uuid.uuid4()),
        }
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name=new_user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata_rec}),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])},
        )
        self.assert200(r)
        rec_event_id = r.json["id"]
        # Deleting notification
        r_del_not = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.delete_feed_events', user_name=self.user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.NOTIFICATION.value, 'id': notification_event_id}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert200(r_del_not)

        # Checking if notification still exists
        r_not = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        payload_not = r_not.json["payload"]
        self.assertEqual(0, payload_not["count"])
        self.assertEqual(self.user["musicbrainz_id"], payload_not["user_id"])

        # Deleting recommendation event
        r_del_rec = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.delete_feed_events', user_name=new_user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.RECORDING_RECOMMENDATION.value, 'id': rec_event_id}),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])}
        )
        self.assert200(r_del_rec)

        # Checking if recording recommendation still exists
        r_rec = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=new_user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])}
        )
        payload_rec = r_rec.json["payload"]
        self.assertEqual(0, payload_rec["count"])
        self.assertEqual(new_user["musicbrainz_id"], payload_rec["user_id"])

    def test_delete_feed_events_token_for_authorization(self):
        # Adding notification to the db
        metadata_not = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(self.db_conn, 11, "troi-bot")
        self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_notification_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata_not}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        # Attempt to delete notifications by passing no Auth header
        r_not = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.delete_feed_events',
                                user_name=self.user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.NOTIFICATION.value, 'id': 1}),
        )
        self.assert401(r_not)
        # Adding recording recommendation to db
        new_user = db_user.get_or_create(self.db_conn, 2, "riksucks")
        metadata_rec = {
            'artist_name': 'Nujabes',
            'track_name': 'Aruarian Dance',
            'recording_msid': str(uuid.uuid4()),
        }
        self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_recording_recommendation_event',
                                user_name=new_user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata_rec}),
            headers={'Authorization': 'Token {}'.format(new_user['auth_token'])},
        )
        # Deleting recommendation event
        r_rec = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.delete_feed_events',
                                user_name=new_user["musicbrainz_id"]),
            data=json.dumps({'event_type': UserTimelineEventType.RECORDING_RECOMMENDATION.value, 'id': 2}),
            headers={'Authorization': 'Token l33thaxors'}
        )
        self.assert401(r_rec)

    @mock.patch("listenbrainz.db.user_timeline_event.delete_user_timeline_event", side_effect=DatabaseException)
    def test_delete_feed_events_for_db_exceptions(self, mock_create_event):
        # see test_unhide_events_for_database_exception for details on this
        self.app.config["TESTING"] = False

        # Adding notification to the db
        metadata_not = {"message": 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'}
        approved_user = db_user.get_or_create(self.db_conn, 11, "troi-bot")
        self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_notification_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata_not}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        # Attempt to delete notification
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.delete_feed_events',
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
        approved_user = db_user.get_or_create(self.db_conn, 11, "troi-bot")
        self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_notification_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata_not}),
            headers={'Authorization': 'Token {}'.format(approved_user['auth_token'])}
        )
        # Attempt to delete notification with empty JSON, should throw bad request error
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.delete_feed_events',
                                user_name=self.user["musicbrainz_id"]),
            data=json.dumps({}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])}
        )
        self.assert400(r)

    def test_hide_events(self):
        # creating a new user
        new_user = db_user.get_or_create(self.db_conn, 2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # user starts following riksucks
        db_user_relationship.insert(self.db_conn, self.user['id'], new_user['id'], 'follow')

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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
        new_user = db_user.get_or_create(self.db_conn, 2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # user starts following riksucks
        db_user_relationship.insert(self.db_conn, self.user['id'], new_user['id'], 'follow')

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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
        new_user = db_user.get_or_create(self.db_conn, 2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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
        new_user = db_user.get_or_create(self.db_conn, 2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # user starts following riksucks
        db_user_relationship.insert(self.db_conn, self.user['id'], new_user['id'], 'follow')

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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
        new_user = db_user.get_or_create(self.db_conn, 2, 'riksucks')
        # creating an event
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # user starts following riksucks
        db_user_relationship.insert(self.db_conn, self.user['id'], new_user['id'], 'follow')

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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
            self.db_conn,
            self.user['id'],
            UserTimelineEventType.RECORDING_RECOMMENDATION.value,
            1
        )

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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
            self.db_conn,
            self.user['id'],
            UserTimelineEventType.RECORDING_RECOMMENDATION.value,
            1
        )

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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
            self.db_conn,
            self.user['id'],
            UserTimelineEventType.RECORDING_RECOMMENDATION.value,
            1
        )

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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
            self.db_conn,
            self.user['id'],
            UserTimelineEventType.RECORDING_RECOMMENDATION.value,
            1
        )

        # send request to hide event
        r = self.client.post(
            self.custom_url_for(
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

    @requests_mock.Mocker()
    def test_critiquebrainz_writes_an_event_to_the_database_and_returns_event_data(self, mock_requests):
        review_id = str(uuid.uuid4())
        mock_requests.post(CRITIQUEBRAINZ_REVIEW_SUBMIT_URL, status_code=200, json={'id': review_id})

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': self.review_metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert200(r)
        data = r.json
        self.assertEqual('critiquebrainz_review', data["event_type"])
        self.assertEqual(self.review_metadata["entity_id"], data["metadata"]["entity_id"])
        self.assertEqual(self.review_metadata["entity_name"], data["metadata"]["entity_name"])
        self.assertEqual(review_id, data["metadata"]["review_id"])

        events = db_user_timeline_event.get_cb_review_events(
            self.db_conn,
            user_ids=[self.user['id']],
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=1,
        )
        self.assertEqual(1, len(events))
        self.assertEqual('Heart Shaker', events[0].metadata.entity_name)
        self.assertEqual(review_id, events[0].metadata.review_id)

    def test_critiquebrainz_checks_auth_token_for_authorization(self):
        # send a request without a token
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': self.review_metadata}),
        )
        self.assert401(r)

        # send a request with an incorrect token
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': self.review_metadata}),
            headers={'Authorization': 'Token DSdsa asdasd sad asd'},
        )
        self.assert401(r)

        # check that no events were created in the database
        events = db_user_timeline_event.get_cb_review_events(
            self.db_conn,
            user_ids=[self.user['id']],
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=1,
        )
        self.assertListEqual([], events)

    def test_critiquebrainz_validates_metadata_json(self):
        metadata = {}

        # empty metadata should 400
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert400(r)

    @requests_mock.Mocker()
    @mock.patch('listenbrainz.db.user_timeline_event.create_user_cb_review_event', side_effect=DatabaseException)
    def test_critiquebrainz_handles_database_exceptions(self, mock_requests, mock_create_event):
        review_id = str(uuid.uuid4())
        mock_requests.post(CRITIQUEBRAINZ_REVIEW_SUBMIT_URL, status_code=200, json={'id': review_id})
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': self.review_metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert500(r)
        data = json.loads(r.data)
        self.assertEqual('An unknown error occured.', data['error'])

    @requests_mock.Mocker()
    def test_critiquebrainz_handles_cb_api_exceptions(self, mock_requests):
        mock_requests.post(
            CRITIQUEBRAINZ_REVIEW_SUBMIT_URL,
            status_code=500,
            json={'code': 500, 'description': 'Internal Server Error'}
        )
        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': self.review_metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert500(r)
        data = json.loads(r.data)
        self.assertEqual("Something went wrong. Please try again later.", data['error'])

    @requests_mock.Mocker()
    def test_get_cb_review_events(self, mock_requests):
        self.maxDiff = None

        user_2 = db_user.get_or_create(self.db_conn, 201, 'not your friendly neighborhood spider-man')
        with self.app.app_context():
            CritiqueBrainzService().add_new_user(user_2['id'], {
                "access_token": "bazbar",
                "refresh_token": "bazfoo",
                "expires_in": 3600
            })

        metadata_1 = {
            "entity_name": "Heart Shaker",
            "entity_id": "cea67a92-db08-4950-bdc6-6d52fc622243",
            "entity_type": "recording",
            "rating": 5,
            "language": "en",
            "text": "Review text goes here ...",
        }
        metadata_2 = {
            "entity_name": "Britney Spears",
            "entity_id": "45a663b5-b1cb-4a91-bff6-2bef7bbfdd76",
            "entity_type": "artist",
            "rating": 4,
            "language": "en",
            "text": "Review2 text goes here ...",
        }
        metadata_3 = {
            "entity_name": "Oops! …I Did It Again",
            "entity_id": "44abd7d3-c593-4587-a109-6d9582f13f36",
            "entity_type": "recording",
            "rating": 5,
            "language": "en",
            "text": "Review3 text goes here ...",
        }
        review_mbid_1 = str(uuid.uuid4())
        review_mbid_2 = str(uuid.uuid4())
        review_mbid_3 = str(uuid.uuid4())

        mock_requests.post(CRITIQUEBRAINZ_REVIEW_SUBMIT_URL, [
            {"status_code": 200, "json": {"id": review_mbid_1}},
            {"status_code": 200, "json": {"id": review_mbid_2}},
            {"status_code": 200, "json": {"id": review_mbid_3}},
        ])

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata_1}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert200(r)
        print(r.json)
        review_event_id_1 = r.json["id"]

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({'metadata': metadata_2}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert200(r)
        review_event_id_2 = r.json["id"]

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_user_cb_review_event',
                                user_name=user_2['musicbrainz_id']),
            data=json.dumps({'metadata': metadata_3}),
            headers={'Authorization': 'Token {}'.format(user_2['auth_token'])},
        )
        self.assert200(r)
        review_event_id_3 = r.json["id"]

        # we created 3 reviews originally so LB db has record of 3 review events but we intentionally return
        # 2 reviews from CB so that we can test the case of if a review is deleted from CB, LB side just skips
        # it without erring
        mock_requests.get(CRITIQUEBRAINZ_REVIEW_FETCH_URL, status_code=200, json={
            "reviews": {
                review_mbid_1: {
                    "entity_type": metadata_1["entity_type"],
                    "text": metadata_1["text"],
                    "rating": metadata_1["rating"],
                },
                review_mbid_3: {
                    "entity_type": metadata_3["entity_type"],
                    "text": metadata_3["text"],
                    "rating": metadata_3["rating"],
                }
            }
        })

        db_user_relationship.insert(self.db_conn, self.user['id'], user_2['id'], 'follow')

        r = self.client.get(
            self.custom_url_for('user_timeline_event_api_bp.user_feed', user_name=self.user['musicbrainz_id']),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            query_string={'min_ts': 0, 'max_ts': int(time.time()) + 1000}
        )
        self.assert200(r)

        data = r.json["payload"]
        events_map = {event["id"]: event for event in data["events"]}

        self.assertIn(review_event_id_1, events_map)
        review_event_1 = events_map[review_event_id_1]
        self.assertEqual(metadata_1["entity_type"], review_event_1["metadata"]["entity_type"])
        self.assertEqual(metadata_1["entity_id"], review_event_1["metadata"]["entity_id"])
        self.assertEqual(metadata_1["entity_name"], review_event_1["metadata"]["entity_name"])
        self.assertEqual(metadata_1["rating"], review_event_1["metadata"]["rating"])
        self.assertEqual(metadata_1["text"], review_event_1["metadata"]["text"])
        self.assertEqual(review_mbid_1, review_event_1["metadata"]["review_mbid"])

        self.assertNotIn(review_event_id_2, events_map)

        self.assertIn(review_event_id_3, events_map)
        review_event_3 = events_map[review_event_id_3]
        self.assertEqual(metadata_3["entity_type"], review_event_3["metadata"]["entity_type"])
        self.assertEqual(metadata_3["entity_id"], review_event_3["metadata"]["entity_id"])
        self.assertEqual(metadata_3["entity_name"], review_event_3["metadata"]["entity_name"])
        self.assertEqual(metadata_3["rating"], review_event_3["metadata"]["rating"])
        self.assertEqual(metadata_3["text"], review_event_3["metadata"]["text"])
        self.assertEqual(review_mbid_3, review_event_3["metadata"]["review_mbid"])

    def test_personal_recommendation_writes_to_db(self):
        # Let's create 2 users, who follow the request sender
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')
        db_user_relationship.insert(self.db_conn, user_two['id'], self.user['id'], 'follow')
        metadata = {
            "recording_mbid": str(uuid.uuid4()),
            "recording_msid": str(uuid.uuid4()),
            "users": [user_one['musicbrainz_id'], user_two['musicbrainz_id']],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert200(r)

        events = db_user_timeline_event.get_personal_recommendation_events_for_feed(
            self.db_conn,
            user_id=self.user['id'],
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=50
        )

        self.assertEqual(1, len(events))

        received = events[0].metadata.dict(exclude_none=True)
        self.assertEqual(metadata, received)

    def test_personal_recommendation_checks_auth_token(self):
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')
        db_user_relationship.insert(self.db_conn, user_two['id'], self.user['id'], 'follow')
        metadata = {
            "track_name": "Natkhat",
            "artist_name": "Seedhe Maut",
            "release_name": "न",
            "recording_mbid": str(uuid.uuid4()),
            "recording_msid": str(uuid.uuid4()),
            "users": [user_one['musicbrainz_id'], user_two['musicbrainz_id']],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
        )
        self.assert401(r)

    def test_personal_recommendation_checks_json_metadata(self):
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')
        db_user_relationship.insert(self.db_conn, user_two['id'], self.user['id'], 'follow')
        metadata = {}

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert400(r)

    @mock.patch('listenbrainz.db.user_timeline_event.create_personal_recommendation_event',
                side_effect=DatabaseException)
    def test_personal_recommendation_handles_db_exceptions(self, mock_create_event):
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')
        db_user_relationship.insert(self.db_conn, user_two['id'], self.user['id'], 'follow')
        metadata = {
            "recording_mbid": str(uuid.uuid4()),
            "recording_msid": str(uuid.uuid4()),
            "users": [user_one['musicbrainz_id'], user_two['musicbrainz_id']],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert500(r)
        data = json.loads(r.data)
        self.assertEqual('Something went wrong, please try again.', data['error'])

    def test_personal_recommendation_errors_when_different_token_used(self):
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')
        db_user_relationship.insert(self.db_conn, user_two['id'], self.user['id'], 'follow')
        metadata = {
            "recording_mbid": str(uuid.uuid4()),
            "recording_msid": str(uuid.uuid4()),
            "users": [user_one['musicbrainz_id'], user_two['musicbrainz_id']],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(user_one['auth_token'])},
        )
        self.assert403(r)
        data = json.loads(r.data)
        self.assertEqual("You don't have permissions to post to this user's timeline.", data['error'])

    def test_personal_recommendation_not_for_non_followers(self):
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        # Only riksucks is following
        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')

        metadata = {
            "recording_mbid": str(uuid.uuid4()),
            "recording_msid": str(uuid.uuid4()),
            "users": [user_one['musicbrainz_id'], user_two['musicbrainz_id']],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert400(r)
        data = json.loads(r.data)
        self.assertEqual("You cannot recommend tracks to non-followers! These people don't follow you ['hrik2001']",
                         data['error'])

    def test_personal_recommendation_not_for_non_followers_peter_k(self):
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')

        metadata = {
            "recording_mbid": str(uuid.uuid4()),
            "recording_msid": str(uuid.uuid4()),
            "users": ["peter k"],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert400(r)
        data = json.loads(r.data)
        self.assertEqual("You cannot recommend tracks to non-followers! These people don't follow you ['peter k']",
                         data['error'])

    def test_personal_recommendation_stays_after_unfollowing(self):
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')
        db_user_relationship.insert(self.db_conn, user_two['id'], self.user['id'], 'follow')

        metadata = {
            "recording_mbid": str(uuid.uuid4()),
            "recording_msid": str(uuid.uuid4()),
            "users": [user_one['musicbrainz_id'], user_two['musicbrainz_id']],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )

        self.assert200(r)
        db_user_relationship.delete(self.db_conn, user_two['id'], self.user['id'], 'follow')

        events = db_user_timeline_event.get_personal_recommendation_events_for_feed(
            self.db_conn,
            user_id=self.user['id'],
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=50
        )

        self.assertEqual(1, len(events))

        received = events[0].metadata.dict(exclude_none=True)
        self.assertEqual(metadata["blurb_content"], received["blurb_content"])
        self.assertEqual(metadata["recording_msid"], received["recording_msid"])
        self.assertEqual(metadata["recording_mbid"], received["recording_mbid"])
        self.assertCountEqual(metadata["users"], received["users"])

    def test_personal_recommendation_user_deleted(self):
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')

        metadata = {
            "recording_mbid": str(uuid.uuid4()),
            "recording_msid": str(uuid.uuid4()),
            "users": [user_one['musicbrainz_id']],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )

        self.assert200(r)
        db_user.delete(self.db_conn, user_one['id'])

        events = db_user_timeline_event.get_personal_recommendation_events_for_feed(
            self.db_conn,
            user_id=self.user['id'],
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=50
        )

        self.assertEqual(1, len(events))

        received = events[0].metadata.dict(exclude_none=True)
        self.assertEqual(metadata["blurb_content"], received["blurb_content"])
        self.assertEqual(metadata["recording_msid"], received["recording_msid"])
        self.assertEqual(metadata["recording_mbid"], received["recording_mbid"])
        self.assertCountEqual([], received["users"])

    def test_personal_recommendation_mbid_only(self):
        """ Test that we can recommend a recording with only mbid """
        # Let's create 2 users, who follow the request sender
        user_one = db_user.get_or_create(self.db_conn, 2, "riksucks")
        user_two = db_user.get_or_create(self.db_conn, 3, "hrik2001")

        db_user_relationship.insert(self.db_conn, user_one['id'], self.user['id'], 'follow')
        db_user_relationship.insert(self.db_conn, user_two['id'], self.user['id'], 'follow')
        metadata = {
            "recording_mbid": "34c208ee-2de7-4d38-b47e-907074866dd3",
            "users": [user_one['musicbrainz_id'], user_two['musicbrainz_id']],
            "blurb_content": "Try out these new people in Indian Hip-Hop!"
        }

        r = self.client.post(
            self.custom_url_for('user_timeline_event_api_bp.create_personal_recommendation_event',
                                user_name=self.user['musicbrainz_id']),
            data=json.dumps({"metadata": metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert200(r)

        events = db_user_timeline_event.get_personal_recommendation_events_for_feed(
            self.db_conn,
            user_id=self.user['id'],
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=50
        )

        self.assertEqual(1, len(events))

        received = events[0].metadata.dict(exclude_none=True)
        self.assertDictEqual(received, metadata)
