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
        self.user = db_user.get_or_create('iliekcomputers')
        self.weirduser = db_user.get_or_create('weird\\user name')

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


    def test_info_valid_stats(self):
        db_stats.insert_user_stats(
            user_id=self.user['id'],
            artists={},
            recordings={},
            releases={},
            artist_count=0,
        )

        self.temporary_login(self.user['id'])
        response = self.client.get(url_for('profile.info'))
        self.assert200(response)
        self.assertIn('Please wait until our next batch', str(response.data))


    @patch('listenbrainz.webserver.views.api_tools.publish_data_to_queue')
    def test_request_stats(self, mock_publish):
        self.temporary_login(self.user['id'])
        response = self.client.get(url_for('profile.request_stats'), follow_redirects=True)
        self.assertStatus(response, 200)
        self.assertIn('You have been added to the stats calculation queue', str(response.data))

        db_stats.insert_user_stats(
            user_id=self.user['id'],
            artists={},
            recordings={},
            releases={},
            artist_count=0,
        )

        response = self.client.get(url_for('profile.request_stats'), follow_redirects=True)
        self.assertStatus(response, 200)
        self.assertIn('please wait until the next interval', str(response.data))


    def test_delete(self):
        self.temporary_login(self.user['id'])
        r = self.client.get(url_for('profile.delete'))
        self.assert200(r)

        r = self.client.post(url_for('profile.delete'), data={'token': self.user['auth_token']})
        self.assertRedirects(r, '/')
        user = db_user.get(self.user['id'])
        self.assertIsNone(user)
