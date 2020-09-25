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

from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from flask import url_for, current_app

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import time
import json

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
        # send a listen for the following_user_1
        payload['payload'][0]['listened_at'] = ts
        response = self.send_data(payload, user=self.following_user_1)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # send a listen with a higher timestamp for following_user_2
        payload['payload'][0]['listened_at'] = ts + 1
        response = self.send_data(payload, user=self.following_user_2)
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

        # This sleep allows for the timescale subscriber to take its time in getting
        # the listen submitted from redis and writing it to timescale.
        time.sleep(2)

        response = self.client.get(url_for('api_v1.user_feed', user_name=self.main_user['musicbrainz_id']))
        self.assert200(response)
        payload = response.json['payload']

        # should contain 2 listens
        self.assertEqual(2, payload['count'])

        # first listen should have higher timestamp and user should be following_2
        self.assertEqual(ts + 1, payload['feed'][0]['listened_at'])
        self.assertEqual('following_2', payload['feed'][0]['user_name'])

        # second listen should have lower timestamp and user should be following_1
        self.assertEqual(ts, payload['feed'][1]['listened_at'])
        self.assertEqual('following_1', payload['feed'][1]['user_name'])


    def test_it_returns_not_found_for_non_existent_user(self):
        r = self.client.get('/1/user/doesntexistlol/feed/listens')
        self.assert404(r)

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
        r = self.client.get('/1/user/param/feed/listens', query_string={'max_ts': ts +  2})
        self.assert200(r)
        self.assertEqual(2, r.json['payload']['count'])

        # max_ts = 4, should have sent back 6 listens
        r = self.client.get('/1/user/param/feed/listens', query_string={'max_ts': ts +  2})
        self.assert200(r)
        self.assertEqual(2, r.json['payload']['count'])

        # min_ts = 1, should have sent back 4 listens
        r = self.client.get('/1/user/param/feed/listens', query_string={'min_ts': ts + 1})
        self.assert200(r)
        self.assertEqual(4, r.json['payload']['count'])

        # min_ts = 2, should have sent back 2 listens
        r = self.client.get('/1/user/param/feed/listens', query_string={'min_ts': ts + 2})
        self.assert200(r)
        self.assertEqual(2, r.json['payload']['count'])

        # min_ts = 1, max_ts = 3, should have sent back 2 listens
        r = self.client.get('/1/user/param/feed/listens', query_string={'min_ts': ts + 1, 'max_ts': ts + 3})
        self.assert200(r)
        self.assertEqual(2, r.json['payload']['count'])

        # should honor count
        r = self.client.get('/1/user/param/feed/listens', query_string={'count': 1})
        self.assert200(r)
        self.assertEqual(1, r.json['payload']['count'])
