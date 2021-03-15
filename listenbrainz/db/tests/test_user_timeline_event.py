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

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.exceptions import DatabaseException

from data.model.user_timeline_event import UserTimelineEvent, UserTimelineEventMetadata, UserTimelineEventType, \
    RecordingRecommendationMetadata


class UserTimelineEventDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(UserTimelineEventDatabaseTestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'friendly neighborhood spider-man')
        events = db_user_timeline_event.get_user_track_recommendation_events(
            user_id=self.user['id'],
            count=1,
        )
        self.assertListEqual([], events)

    def test_it_adds_rows_to_the_database(self):
        event = db_user_timeline_event.create_user_timeline_event(
            user_id=self.user['id'],
            event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )
        events = db_user_timeline_event.get_user_track_recommendation_events(
            user_id=self.user['id'],
            count=1,
        )
        self.assertEqual(1, len(events))
        self.assertEqual(event.id, events[0].id)
        self.assertEqual(event.created, events[0].created)
        self.assertEqual('Sunflower', events[0].metadata.track_name)

    @mock.patch('listenbrainz.db.engine.connect', side_effect=Exception)
    def test_it_raises_database_exceptions_if_something_goes_wrong(self, mock_db_connect):
        with self.assertRaises(DatabaseException):
            db_user_timeline_event.create_user_timeline_event(
                user_id=self.user['id'],
                event_type=UserTimelineEventType.RECORDING_RECOMMENDATION,
                metadata=RecordingRecommendationMetadata(
                    track_name="Sunflower",
                    artist_name="Swae Lee & Post Malone",
                    recording_msid=str(uuid.uuid4()),
                    artist_msid=str(uuid.uuid4()),
                )
            )

    def test_create_user_track_recommendation_sets_event_type_correctly(self):
        event = db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )
        self.assertEqual(UserTimelineEventType.RECORDING_RECOMMENDATION, event.event_type)

    def test_get_events_only_gets_events_for_the_specified_user(self):
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )
        new_user = db_user.get_or_create(2, 'captain america')
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Fade",
                artist_name="Kanye West",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )
        events = db_user_timeline_event.get_user_track_recommendation_events(
            user_id=new_user['id'],
        )
        self.assertEqual(1, len(events))
        self.assertEqual(new_user['id'], events[0].user_id)

    def test_get_events_for_feed_returns_events(self):
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )

        new_user = db_user.get_or_create(2, 'superman')
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )

        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
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
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Da Funk",
                artist_name="Daft Punk",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )

        time.sleep(3)
        new_user = db_user.get_or_create(4, 'new_user')
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Da Funk",
                artist_name="Daft Punk",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )

        # max_ts is too low, won't return anything
        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            user_ids=(self.user['id'], new_user['id']),
            min_ts=0,
            max_ts=ts,
            count=50,
        )
        self.assertListEqual([], events)

        # check that it honors min_ts as well
        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            user_ids=(self.user['id'], new_user['id']),
            min_ts=ts + 1,
            max_ts=ts + 10,
            count=50,
        )
        self.assertEqual(1, len(events))

    def test_get_events_for_feed_honors_count_parameter(self):
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.user['id'],
            metadata=RecordingRecommendationMetadata(
                track_name="Da Funk",
                artist_name="Daft Punk",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )

        events = db_user_timeline_event.get_recording_recommendation_events_for_feed(
            user_ids=(self.user['id'],),
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=1,
        )

        # 2 events exist, should return only one, the one that is newer
        self.assertEqual(1, len(events))
        self.assertEqual('Da Funk', events[0].metadata.track_name)
