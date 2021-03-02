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
import uuid

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.exceptions import DatabaseException

from data.model.user_timeline_event import UserTimelineEvent, UserTimelineEventMetadata, UserTimelineEventType

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
            metadata=UserTimelineEventMetadata(
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
                metadata=UserTimelineEventMetadata(
                    track_name="Sunflower",
                    artist_name="Swae Lee & Post Malone",
                    recording_msid=str(uuid.uuid4()),
                    artist_msid=str(uuid.uuid4()),
                )
            )

    def test_create_user_track_recommendation_sets_event_type_correctly(self):
        event = db_user_timeline_event.create_user_track_recommendation_event(
            user_id=self.user['id'],
            metadata=UserTimelineEventMetadata(
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
            metadata=UserTimelineEventMetadata(
                track_name="Sunflower",
                artist_name="Swae Lee & Post Malone",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )
        new_user = db_user.get_or_create(2, 'captain america')
        db_user_timeline_event.create_user_track_recommendation_event(
            user_id=new_user['id'],
            metadata=UserTimelineEventMetadata(
                track_name="Fade",
                artist_name="Kanye West",
                recording_msid=str(uuid.uuid4()),
                artist_msid=str(uuid.uuid4()),
            )
        )
        events = db_user_timeline_event.get_user_track_recommendation_events(
            user_id=self.user['id'],
        )
        self.assertEqual(1, len(events))
        self.assertEqual(new_user['id'], events[0].user_id)
