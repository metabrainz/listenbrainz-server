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
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
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
            '/1/user-timeline-event/create-user-recommendation/recording',
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
            '/1/user-timeline-event/create-user-recommendation/recording',
            data=json.dumps({'metadata': metadata}),
        )
        self.assert401(r)

        # send a request with an incorrect token
        r = self.client.post(
            '/1/user-timeline-event/create-user-recommendation/recording',
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
            '/1/user-timeline-event/create-user-recommendation/recording',
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
            '/1/user-timeline-event/create-user-recommendation/recording',
            data=json.dumps({'metadata': metadata}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
        )
        self.assert500(r)
        data = json.loads(r.data)
        self.assertEqual('Something went wrong, please try again.', data['error'])
