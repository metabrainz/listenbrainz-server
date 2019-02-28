# -*- coding: utf-8 -*-

from listenbrainz import db
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.exceptions import DatabaseException

import listenbrainz.db.user as db_user
import listenbrainz.db.follow_list as db_follow_list


class FollowListTestCase(DatabaseTestCase):

    def setUp(self):
        super(FollowListTestCase, self).setUp()
        self.main_user = db_user.get_or_create(1, 'iliekcomputers')
        self.followed_user_1 = db_user.get_or_create(2, 'followed_user_1')
        self.followed_user_2 = db_user.get_or_create(3, 'followed_user_2')
        self.followed_user_3 = db_user.get_or_create(4, 'followed_user_3')


    def test_get_and_create(self):
        uncreated_list = db_follow_list.get(1)
        self.assertIsNone(uncreated_list)

        with db.engine.connect() as connection:
            list_id = db_follow_list._create(connection, 'test follow list', self.main_user['id'])
        created_list = db_follow_list.get(list_id)
        self.assertEqual(created_list['id'], list_id)
        self.assertEqual(created_list['name'], 'test follow list')
        self.assertEqual(created_list['creator'], self.main_user['id'])
        self.assertIn('created', created_list)
        self.assertIn('last_saved', created_list)

    def test_add_and_remove_users(self):

        with db.engine.connect() as connection:
            list_id = db_follow_list._create(connection, 'test follow list', self.main_user['id'])
            members = db_follow_list._get_members(connection, list_id)
            self.assertListEqual(members, [])

            db_follow_list._add_users(connection, list_id, [2, 3, 4])
            members = db_follow_list._get_members(connection, list_id)
            self.assertEqual(len(members), 3)
            self.assertEqual(members[0]['user_id'], 2)
            self.assertEqual(members[0]['priority'], 2)
            self.assertEqual(members[1]['user_id'], 3)
            self.assertEqual(members[1]['priority'], 1)
            self.assertEqual(members[2]['user_id'], 4)
            self.assertEqual(members[2]['priority'], 0)

            db_follow_list._remove_users(connection, list_id)
            members = db_follow_list._get_members(connection, list_id)
            self.assertListEqual(members, [])

    def test_save(self):
        list_id = db_follow_list.save('test follow list', self.main_user['id'], [2, 3, 4])
        created_list = db_follow_list.get(list_id)
        self.assertEqual(created_list['id'], list_id)
        self.assertEqual(created_list['name'], 'test follow list')
        self.assertEqual(created_list['creator'], self.main_user['id'])
        self.assertIn('created', created_list)
        self.assertIn('last_saved', created_list)

        with db.engine.connect() as connection:
            members = db_follow_list._get_members(connection, list_id)
            self.assertEqual(len(members), 3)
            self.assertEqual(members[0]['user_id'], 2)
            self.assertEqual(members[0]['priority'], 2)
            self.assertEqual(members[1]['user_id'], 3)
            self.assertEqual(members[1]['priority'], 1)
            self.assertEqual(members[2]['user_id'], 4)
            self.assertEqual(members[2]['priority'], 0)

        # try to save another list with same name for the same user
        with self.assertRaises(DatabaseException):
            db_follow_list.save('test follow list', self.main_user['id'], [2, 3, 4])

    def test_update(self):
        list_id = db_follow_list.save('test follow list', self.main_user['id'], [2, 3, 4])
        created_list = db_follow_list.get(list_id)
        self.assertEqual(created_list['id'], list_id)
        self.assertEqual(created_list['name'], 'test follow list')
        self.assertEqual(created_list['creator'], self.main_user['id'])
        old_created = created_list['created']
        old_saved = created_list['last_saved']


        with db.engine.connect() as connection:
            members = db_follow_list._get_members(connection, list_id)
            self.assertEqual(len(members), 3)
            self.assertEqual(members[0]['user_id'], 2)
            self.assertEqual(members[0]['priority'], 2)
            self.assertEqual(members[1]['user_id'], 3)
            self.assertEqual(members[1]['priority'], 1)
            self.assertEqual(members[2]['user_id'], 4)
            self.assertEqual(members[2]['priority'], 0)

        db_follow_list.update(list_id, 'new name', [3, 4])
        updated_list = db_follow_list.get(list_id)
        self.assertEqual(updated_list['id'], list_id)
        self.assertEqual(updated_list['name'], 'new name')
        self.assertEqual(updated_list['created'], old_created)
        self.assertGreater(updated_list['last_saved'], old_saved)

        with db.engine.connect() as connection:
            members = db_follow_list._get_members(connection, list_id)
            self.assertEqual(len(members), 2)
            self.assertEqual(members[0]['user_id'], 3)
            self.assertEqual(members[0]['priority'], 1)
            self.assertEqual(members[1]['user_id'], 4)
            self.assertEqual(members[1]['priority'], 0)


    def test_get_latest(self):
        list_id = db_follow_list.save('test follow list 1', self.main_user['id'], [2, 3, 4])
        list_1 = db_follow_list.get(list_id)
        list_id = db_follow_list.save('test follow list 2', self.main_user['id'], [3, 4])
        list_2 = db_follow_list.get(list_id)

        latest_list = db_follow_list.get_latest(self.main_user['id'])
        self.assertEqual(latest_list['id'], list_2['id'])

        db_follow_list.update(list_1['id'], 'new name', [4])
        latest_list = db_follow_list.get_latest(self.main_user['id'])
        self.assertEqual(latest_list['id'], list_1['id'])
