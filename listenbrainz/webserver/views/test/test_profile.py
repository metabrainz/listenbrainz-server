import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import time

from flask import url_for
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase
from unittest.mock import patch


class ProfileViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])
        self.weirduser = db_user.get_or_create(2, 'weird\\user name')
        db_user.agree_to_gdpr(self.weirduser['musicbrainz_id'])

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def test_reset_import_timestamp_get(self):
        self.temporary_login(self.user['id'])
        response = self.client.get(url_for('profile.reset_latest_import_timestamp'))
        self.assertTemplateUsed('profile/resetlatestimportts.html')
        self.assert200(response)

    def test_profile_view(self):
        """Tests the user info view and makes sure auth token is present there"""
        self.temporary_login(self.user['id'])
        response = self.client.get(url_for('profile.info', user_name=self.user['musicbrainz_id']))
        self.assertTemplateUsed('profile/info.html')
        self.assert200(response)
        self.assertIn(self.user['auth_token'], response.data.decode('utf-8'))

    def test_reset_import_timestamp(self):
        self.temporary_login(self.user['id'])
        val = int(time.time())
        db_user.update_latest_import(self.user['musicbrainz_id'], val)

        response = self.client.post(
            url_for('profile.reset_latest_import_timestamp'),
            data={
                'reset': 'yes',
                'token': self.user['auth_token']
            }
        )
        self.assertStatus(response, 302) # should have redirected to the info page
        self.assertRedirects(response, url_for('profile.info'))
        ts = db_user.get(self.user['id'])['latest_import'].strftime('%s')
        self.assertEqual(int(ts), 0)

    def test_reset_import_timestamp_post(self):
        self.temporary_login(self.user['id'])
        val = int(time.time())
        db_user.update_latest_import(self.user['musicbrainz_id'], val)

        response = self.client.post(
            url_for('profile.reset_latest_import_timestamp'),
            data={
                'reset': 'yes',
                'token': self.user['auth_token']
            }
        )
        self.assertStatus(response, 302)  # should have redirected to the import page
        self.assertRedirects(response, url_for('profile.info'))
        ts = db_user.get(self.user['id'])['latest_import'].strftime('%s')
        self.assertEqual(int(ts), 0)

    def test_user_info_not_logged_in(self):
        """Tests user info view when not logged in"""
        profile_info_url = url_for('profile.info')
        response = self.client.get(profile_info_url)
        self.assertStatus(response, 302)
        self.assertRedirects(response, url_for('login.index', next=profile_info_url))
