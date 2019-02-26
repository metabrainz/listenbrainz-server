from flask import url_for
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase

import listenbrainz.db.user as db_user


class FollowViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])

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
