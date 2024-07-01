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


import listenbrainz.db.user as db_user
import listenbrainz.db.user_timeline_event as db_user_timeline_event
from unittest import mock
import time
import uuid

from listenbrainz.db.model.review import CBReviewTimelineMetadata
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.exceptions import DatabaseException

from listenbrainz.db.model.user_timeline_event import UserTimelineEventType, RecordingRecommendationMetadata, \
    NotificationMetadata, WritePersonalRecordingRecommendationMetadata


class UserTimelineEventDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(UserTimelineEventDatabaseTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, 'friendly neighborhood spider-man')

    def test_it_adds_rows_to_the_database(self):
        recording_msid = str(uuid.uuid4())
        event = db_user_timeline_event.create_user_timeline_event(
            self.db_conn,
            user_id=self.user['id'],
            event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
            metadata=RecordingRecommendationMetadata(recording_msid=recording_msid)
        )
        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=[self.user['id']],
            min_ts=0,
            max_ts=time.time(),
            count=1,
        )
        self.assertEqual(1, len(events))
        self.assertEqual(event.id, events[0].id)
        self.assertEqual(event.created, events[0].created)
        self.assertEqual(recording_msid, events[0].metadata.recording_msid)

    def test_it_raises_database_exceptions_if_something_goes_wrong(self):
        with mock.patch.object(self.db_conn, "execute", side_effect=Exception), \
                self.assertRaises(DatabaseException):
            db_user_timeline_event.create_user_timeline_event(
                self.db_conn,
                user_id=self.user['id'],
                event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
                metadata=RecordingRecommendationMetadata(recording_msid=str(uuid.uuid4()))
            )

    def test_create_user_track_recommendation_sets_event_type_correctly(self):
        event = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(recording_msid=str(uuid.uuid4()))
        )
        self.assertEqual(UserTimelineEventType.RECORDING_RECOMMENDATION, event.event_type)

    def test_create_user_cb_review_event_sets_event_type_correctly(self):
        event = db_user_timeline_event.create_user_cb_review_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=CBReviewTimelineMetadata(
                review_id="f305b3fd-a040-4cde-b5ce-a926614f5d5d",
                entity_name="Sunflower",
                entity_id="f305b3fd-a040-4cde-b5ce-a926614f5d5d"
            )
        )
        self.assertEqual(UserTimelineEventType.CRITIQUEBRAINZ_REVIEW, event.event_type)

    def test_create_user_notification_event(self):
        message = 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'
        event = db_user_timeline_event.create_user_notification_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=NotificationMetadata(
                creator=self.user['musicbrainz_id'],
                message=message,
            )
        )
        self.assertEqual(self.user['id'], event.user_id)
        self.assertEqual(message, event.metadata.message)
        self.assertEqual(self.user['musicbrainz_id'], event.metadata.creator)
        self.assertEqual(UserTimelineEventType.NOTIFICATION, event.event_type)

    def test_get_events_only_gets_events_for_the_specified_user(self):
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
            )
        )
        new_user = db_user.get_or_create(self.db_conn, 2, 'captain america')
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Fade",
                artist_name="Kanye West",
                recording_msid=str(uuid.uuid4()),
            )
        )
        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=[new_user['id']],
            min_ts=0,
            max_ts=int(time.time()) + 1000,
            count=10
        )
        self.assertEqual(1, len(events))
        self.assertEqual(new_user['id'], events[0].user_id)

    def test_get_events_for_feed_returns_events(self):
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
            )
        )

        new_user = db_user.get_or_create(self.db_conn, 2, 'superman')
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
            )
        )

        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=(self.user['id'], new_user['id']),
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=50,
        )
        self.assertEqual(2, len(events))
        self.assertEqual(new_user['id'], events[0].user_id)
        self.assertEqual(self.user['id'], events[1].user_id)

    def test_get_events_for_feed_honors_time_parameters(self):
        ts = int(time.time())
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
            )
        )
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Da Funk",
                artist_name="Daft Punk",
                recording_msid=str(uuid.uuid4()),
            )
        )

        ts2 = time.time()
        new_user = db_user.get_or_create(self.db_conn, 4, 'new_user')
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Da Funk",
                artist_name="Daft Punk",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # max_ts is too low, won't return anything
        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=(self.user['id'], new_user['id']),
            min_ts=0,
            max_ts=ts,
            count=50,
        )
        self.assertListEqual([], events)

        # check that it honors min_ts as well
        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=(self.user['id'], new_user['id']),
            min_ts=ts2,
            max_ts=ts + 10,
            count=50,
        )
        self.assertEqual(1, len(events))

    def test_get_events_for_feed_honors_count_parameter(self):
        recording_msid_1 = str(uuid.uuid4())
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(recording_msid=recording_msid_1)
        )

        recording_msid_2 = str(uuid.uuid4())
        db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(recording_msid=recording_msid_2)
        )

        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            self.db_conn,
            user_ids=(self.user['id'],),
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=1,
        )

        # 2 events exist, should return only one, the one that is newer
        self.assertEqual(1, len(events))
        self.assertEqual(recording_msid_2, events[0].metadata.recording_msid)

    def test_delete_feed_events(self):
        # creating recording recommendation and checking
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(recording_msid=str(uuid.uuid4()))
        )
        self.assertEqual(UserTimelineEventType.RECORDING_RECOMMENDATION, event_rec.event_type)
        self.assertEqual(self.user['id'], event_rec.user_id)

        # creating a new user for notification
        new_user = db_user.get_or_create(self.db_conn, 2, 'riksucks')
        message = 'You have a <a href="https://listenbrainz.org/non-existent-playlist">playlist</a>'
        event_not = db_user_timeline_event.create_user_notification_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=NotificationMetadata(
                creator=new_user['musicbrainz_id'],
                message=message,
            )
        )
        self.assertEqual(new_user['id'], event_not.user_id)
        self.assertEqual(message, event_not.metadata.message)
        self.assertEqual(new_user['musicbrainz_id'], event_not.metadata.creator)
        self.assertEqual(UserTimelineEventType.NOTIFICATION, event_not.event_type)

        # deleting recording recommendation
        db_user_timeline_event.delete_user_timeline_event(
            self.db_conn,
            id=event_rec.id,
            user_id=self.user["id"],
        )
        event_rec = db_user_timeline_event.get_user_notification_events(
            self.db_conn,
            user_ids=[self.user["id"]],
            min_ts=0,
            max_ts=int(time.time()),
            count=1,
        )
        self.assertEqual(0, len(event_rec))

        # deleting notification
        db_user_timeline_event.delete_user_timeline_event(
            self.db_conn,
            id=event_not.id,
            user_id=new_user["id"],
        )
        event_not = db_user_timeline_event.get_user_notification_events(
            self.db_conn,
            user_ids=[self.user["id"]],
            min_ts=0,
            max_ts=int(time.time()),
            count=1,
        )
        self.assertEqual(0, len(event_not))

    def test_delete_feed_events_for_something_goes_wrong(self):
        # creating recording recommendation
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )
        with mock.patch.object(self.db_conn, "execute", side_effect=Exception), \
                self.assertRaises(DatabaseException):
            # checking if DatabaseException is raised or not
            db_user_timeline_event.delete_user_timeline_event(
                self.db_conn,
                id=event_rec.id,
                user_id=self.user["id"],
            )

    def test_hide_feed_events(self):
        # creating a user
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

        # creating a personal recommendation event
        event_personal_rec = db_user_timeline_event.create_personal_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=WritePersonalRecordingRecommendationMetadata(
                blurb_content="I have seen the FNORDs",
                recording_mbid=str(uuid.uuid4()),
                recording_msid=str(uuid.uuid4()),
                users=list(self.user['musicbrainz_id'])
            )
        )

        # hiding event
        hidden_event = db_user_timeline_event.hide_user_timeline_event(
            self.db_conn,
            user_id=self.user['id'],
            event_type=event_rec.event_type.value,
            event_id=event_rec.id
        )

        # hiding personal rec event
        hidden_personal_event = db_user_timeline_event.hide_user_timeline_event(
            self.db_conn,
            user_id=self.user['id'],
            event_type=UserTimelineEventType.PERSONAL_RECORDING_RECOMMENDATION.value,
            event_id=event_personal_rec.id
        )

        hidden_events = db_user_timeline_event.get_hidden_timeline_events(
            self.db_conn,
            user_id=self.user['id'],
            count=2,
        )

        self.assertEqual(2, len(hidden_events))
        # events are in reverse chronological order
        self.assertEqual(hidden_events[1].event_type.value, 'recording_recommendation')
        self.assertEqual(event_rec.id, hidden_events[1].event_id)
        self.assertEqual(hidden_events[0].event_type.value, 'personal_recording_recommendation')
        self.assertEqual(event_personal_rec.id, hidden_events[0].event_id)

    def test_hide_feed_events_honors_count_parameter(self):
        # creating a user
        new_user = db_user.get_or_create(self.db_conn, 2, 'riksucks')

        # creating an event
        event1 = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # hiding event
        hidden_event = db_user_timeline_event.hide_user_timeline_event(
            self.db_conn,
            user_id=self.user['id'],
            event_type=event1.event_type.value,
            event_id=event1.id
        )

        # creating another event
        event2 = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Aruarian Dance",
                artist_name="Nujabes",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # hiding event
        hidden_event = db_user_timeline_event.hide_user_timeline_event(
            self.db_conn,
            user_id=self.user['id'],
            event_type=event2.event_type.value,
            event_id=event2.id
        )
        hidden_events = db_user_timeline_event.get_hidden_timeline_events(
            self.db_conn,
            user_id=self.user['id'],
            count=1,
        )

        self.assertEqual(1, len(hidden_events))
        self.assertEqual(event2.id, hidden_events[0].event_id)

    def test_hide_feed_events_raises_database_exception(self):
        with mock.patch.object(self.db_conn, "execute", side_effect=Exception), \
                self.assertRaises(DatabaseException):
            # Dummy timeline event
            db_user_timeline_event.hide_user_timeline_event(
                self.db_conn,
                user_id=self.user['id'],
                event_type=UserTimelineEventType.RECORDING_RECOMMENDATION.value,
                event_id=1
            )

    def test_unhide_events(self):
        # creating a user
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

        # hiding event
        hidden_event = db_user_timeline_event.hide_user_timeline_event(
            self.db_conn,
            user_id=self.user['id'],
            event_type=event_rec.event_type.value,
            event_id=event_rec.id
        )

        hidden_events = db_user_timeline_event.get_hidden_timeline_events(
            self.db_conn,
            user_id=self.user['id'],
            count=1,
        )

        self.assertEqual(1, len(hidden_events))
        self.assertEqual(event_rec.id, hidden_events[0].event_id)

        db_user_timeline_event.unhide_timeline_event(
            self.db_conn,
            user=self.user['id'],
            event_type=event_rec.event_type.value,
            event_id=event_rec.id
        )

        hidden_events = db_user_timeline_event.get_hidden_timeline_events(
            self.db_conn,
            user_id=self.user['id'],
            count=1,
        )

        self.assertEqual(0, len(hidden_events))

    def test_unhide_events_for_something_goes_wrong(self):
        # creating recording recommendation
        event_rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn,
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="All Caps",
                artist_name="MF DOOM",
                recording_msid=str(uuid.uuid4()),
            )
        )

        # hiding event
        hidden_event = db_user_timeline_event.hide_user_timeline_event(
            self.db_conn,
            user_id=self.user['id'],
            event_type=event_rec.event_type.value,
            event_id=event_rec.id
        )
        with mock.patch.object(self.db_conn, "execute", side_effect=Exception):
            with self.assertRaises(DatabaseException):
                # checking if DatabaseException is raised or not
                db_user_timeline_event.unhide_timeline_event(
                    self.db_conn,
                    user=self.user['id'],
                    event_type=event_rec.event_type.value,
                    event_id=event_rec.id
                )
