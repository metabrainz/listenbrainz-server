from flask import url_for
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase

import json
import listenbrainz.db.user as db_user


class FollowViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])
        self.user2 = db_user.get_or_create(2, 'iliekcomputers_2')
        db_user.agree_to_gdpr(self.user2['musicbrainz_id'])
        self.user3 = db_user.get_or_create(3, 'iliekcomputers_3')
        db_user.agree_to_gdpr(self.user3['musicbrainz_id'])

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def test_follow_page(self):
        self.temporary_login(self.user['login_id'])
        response = self.client.get(url_for('follow.follow'))
        self.assert200(response)
        self.assertContext('active_section', 'listens')

    def test_user_info_not_logged_in(self):
        """Tests user follow view when not logged in"""
        response = self.client.get(url_for('follow.follow'))
        self.assertStatus(response, 302)

    def test_save_page(self):
        r = self.client.post(
            '/1/follow/save',
            data=json.dumps({
                'name': 'new list',
                'users': ['iliekcomputers_2'],
                'id': None,
            }),
        )
        self.assert401(r)
        self.assertEqual(r.json['code'], 401)

        r = self.client.post(
            '/1/follow/save',
            data=json.dumps({
                'name': 'new list',
                'users': ['iliekcomputers_2'],
                'id': None,
            }),
            headers={"Authorization": "Token {token}".format(token=self.user['auth_token'])},
        )
        self.assert200(r)
        list_id = r.json['list_id']

        r = self.client.get(url_for('follow.follow'))
        self.assertStatus(r, 302) # should redirect to login page

        self.temporary_login(self.user['login_id'])
        r = self.client.get(url_for('follow.follow'))
        self.assert200(r)
        props = json.loads(self.get_context_variable('props'))
        self.assertEqual(props['user']['id'], self.user['id'])
        self.assertEqual(props['follow_list_id'], list_id)
        self.assertEqual(props['follow_list_name'], 'new list')
        self.assertListEqual(props['follow_list'], ['iliekcomputers_2'])

        r = self.client.post(
            '/1/follow/save',
            data=json.dumps({
                'name': 'new list 1',
                'users': ['iliekcomputers_3', 'iliekcomputers_2'],
                'id': list_id,
            }),
            headers={"Authorization": "Token {token}".format(token=self.user['auth_token'])},
        )
        self.assert200(r)

        r = self.client.get(url_for('follow.follow'))
        self.assert200(r)
        props = json.loads(self.get_context_variable('props'))
        self.assertEqual(props['user']['id'], self.user['id'])
        self.assertEqual(props['follow_list_id'], list_id)
        self.assertEqual(props['follow_list_name'], 'new list 1')
        self.assertListEqual(props['follow_list'], ['iliekcomputers_3', 'iliekcomputers_2'])

        # check for list with no users
        r = self.client.post(
            '/1/follow/save',
            data=json.dumps({
                'name': 'new list 1',
                'users': [],
                'id': list_id,
            }),
            headers={"Authorization": "Token {token}".format(token=self.user['auth_token'])},
        )
        self.assert200(r)

        r = self.client.get(url_for('follow.follow'))
        self.assert200(r)
        props = json.loads(self.get_context_variable('props'))
        self.assertEqual(props['user']['id'], self.user['id'])
        self.assertEqual(props['follow_list_id'], list_id)
        self.assertEqual(props['follow_list_name'], 'new list 1')
        self.assertListEqual(props['follow_list'], [])
