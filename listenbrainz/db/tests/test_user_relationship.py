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
import time

from listenbrainz.db.testing import DatabaseTestCase

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship


class UserRelationshipTestCase(DatabaseTestCase):
    def setUp(self):
        super(UserRelationshipTestCase, self).setUp()
        self.main_user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        self.followed_user_1 = db_user.get_or_create(self.db_conn, 2, 'followed_user_1')
        self.followed_user_2 = db_user.get_or_create(self.db_conn, 3, 'followed_user_2')

    def test_insert(self):
        db_user_relationship.insert(
            self.db_conn,
            self.main_user['id'],
            self.followed_user_1['id'],
            'follow'
        )
        self.assertTrue(
            db_user_relationship.is_following_user(
                self.db_conn,
                self.main_user['id'],
                self.followed_user_1['id']
            )
        )

    def test_insert_raises_value_error_for_invalid_relationship(self):
        with self.assertRaises(ValueError):
            db_user_relationship.insert(
                self.db_conn,
                self.main_user['id'],
                self.followed_user_1['id'],
                'idkwhatrelationshipthisis'
            )

    def test_is_following_user(self):
        self.assertFalse(
            db_user_relationship.is_following_user(
                self.db_conn,
                self.main_user['id'],
                self.followed_user_1['id']
            )
        )
        db_user_relationship.insert(
            self.db_conn,
            self.main_user['id'],
            self.followed_user_1['id'],
            'follow'
        )
        self.assertTrue(
            db_user_relationship.is_following_user(
                self.db_conn,
                self.main_user['id'],
                self.followed_user_1['id']
            )
        )

    def test_delete(self):
        db_user_relationship.insert(
            self.db_conn,
            self.main_user['id'],
            self.followed_user_1['id'],
            'follow'
        )
        self.assertTrue(
            db_user_relationship.is_following_user(
                self.db_conn,
                self.main_user['id'],
                self.followed_user_1['id']
            )
        )
        db_user_relationship.delete(
            self.db_conn,
            self.main_user['id'],
            self.followed_user_1['id'],
            'follow'
        )
        self.assertFalse(
            db_user_relationship.is_following_user(
                self.db_conn,
                self.main_user['id'],
                self.followed_user_1['id']
            )
        )

    def test_delete_raises_value_error_for_invalid_relationships(self):
        with self.assertRaises(ValueError):
            db_user_relationship.delete(
                self.db_conn,
                self.main_user['id'],
                self.followed_user_1['id'],
                'idkwhatrelationshipthisis'
            )

    def test_get_followers_of_user_returns_correct_data(self):
        # no relationships yet, should return an empty list
        followers = db_user_relationship.get_followers_of_user(self.db_conn, self.followed_user_1['id'])
        self.assertListEqual(followers, [])

        # add two relationships
        db_user_relationship.insert(
            self.db_conn,
            self.main_user['id'],
            self.followed_user_1['id'],
            'follow'
        )
        self.following_user_1 = db_user.get_or_create(self.db_conn, 3, 'following_user_1')
        db_user_relationship.insert(
            self.db_conn,
            self.following_user_1['id'],
            self.followed_user_1['id'],
            'follow'
        )

        # At this point, the main_user and following_user_1 follow followed_user_1
        # So, if we get the followers of followed_user_1, we'll get back two users
        followers = db_user_relationship.get_followers_of_user(self.db_conn, self.followed_user_1['id'])
        self.assertEqual(2, len(followers))

    def test_get_following_for_user_returns_correct_data(self):

        # no relationships yet, should return an empty list
        following = db_user_relationship.get_following_for_user(self.db_conn, self.main_user['id'])
        self.assertListEqual(following, [])

        # make the main_user follow followed_user_1
        db_user_relationship.insert(
            self.db_conn,
            self.main_user['id'],
            self.followed_user_1['id'],
            'follow'
        )

        # the list of users main_user is following should have 1 element now
        following = db_user_relationship.get_following_for_user(self.db_conn, self.main_user['id'])
        self.assertEqual(1, len(following))

        # make it so that the main user follows two users, followed_user_1 and followed_user_2
        self.followed_user_2 = db_user.get_or_create(self.db_conn, 3, 'followed_user_2')
        db_user_relationship.insert(self.db_conn, self.main_user['id'], self.followed_user_2['id'], 'follow')

        # the list of users main_user is following should have 2 elements now
        following = db_user_relationship.get_following_for_user(self.db_conn, self.main_user['id'])
        self.assertEqual(2, len(following))

    def test_get_follow_events_returns_correct_events(self):
        db_user_relationship.insert(self.db_conn, self.main_user['id'], self.followed_user_1['id'], 'follow')
        db_user_relationship.insert(self.db_conn, self.main_user['id'], self.followed_user_2['id'], 'follow')

        new_user = db_user.get_or_create(self.db_conn, 4, 'new_user')
        db_user_relationship.insert(self.db_conn, self.followed_user_1['id'], new_user['id'], 'follow')

        events = db_user_relationship.get_follow_events(
            self.db_conn,
            user_ids=(self.main_user['id'], self.followed_user_1['id']),
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=50
        )
        self.assertEqual(3, len(events))
        self.assertEqual('followed_user_1', events[0]['user_name_0'])
        self.assertEqual('new_user', events[0]['user_name_1'])

        self.assertEqual('iliekcomputers', events[1]['user_name_0'])
        self.assertEqual('followed_user_2', events[1]['user_name_1'])

        self.assertEqual('iliekcomputers', events[2]['user_name_0'])
        self.assertEqual('followed_user_1', events[2]['user_name_1'])

    def test_get_follow_events_honors_timestamp_parameters(self):
        ts = int(time.time())

        db_user_relationship.insert(self.db_conn, self.main_user['id'], self.followed_user_1['id'], 'follow')
        db_user_relationship.insert(self.db_conn, self.main_user['id'], self.followed_user_2['id'], 'follow')

        ts2 = time.time()

        new_user = db_user.get_or_create(self.db_conn, 4, 'new_user')
        db_user_relationship.insert(self.db_conn, self.followed_user_1['id'], new_user['id'], 'follow')

        # max_ts is too low, won't return anything
        events = db_user_relationship.get_follow_events(
            self.db_conn,
            user_ids=(self.main_user['id'], self.followed_user_1['id']),
            min_ts=0,
            max_ts=ts,
            count=50
        )
        self.assertListEqual([], events)

        # check that it honors min_ts as well
        events = db_user_relationship.get_follow_events(
            self.db_conn,
            user_ids=(self.main_user['id'], self.followed_user_1['id']),
            min_ts=ts2,
            max_ts=ts + 10,
            count=50
        )
        self.assertEqual(1, len(events))

    def test_get_follow_events_honors_count_parameter(self):
        db_user_relationship.insert(self.db_conn, self.main_user['id'], self.followed_user_1['id'], 'follow')
        db_user_relationship.insert(self.db_conn, self.main_user['id'], self.followed_user_2['id'], 'follow')

        new_user = db_user.get_or_create(self.db_conn, 4, 'new_user')
        db_user_relationship.insert(self.db_conn, self.followed_user_1['id'], new_user['id'], 'follow')

        events = db_user_relationship.get_follow_events(
            self.db_conn,
            user_ids=(self.main_user['id'], self.followed_user_1['id']),
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=2,
        )

        # 3 events exist, but should only return 2
        self.assertEqual(2, len(events))

    def test_multiple_users_by_username_following_user(self):
        # Only followed_user_1 follows main user
        db_user_relationship.insert(self.db_conn, self.followed_user_1['id'], self.main_user['id'], 'follow')

        follower_results = db_user_relationship.multiple_users_by_username_following_user(
            self.db_conn,
            followed=self.main_user['id'],
            followers=['followed_user_1', 'followed_user_2']
        )

        self.assertDictEqual({'followed_user_1': True, 'followed_user_2': False}, follower_results)
