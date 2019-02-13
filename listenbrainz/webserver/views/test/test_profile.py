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
        self.temporary_login(self.user['login_id'])
        response = self.client.get(url_for('profile.reset_latest_import_timestamp'))
        self.assertTemplateUsed('profile/resetlatestimportts.html')
        self.assert200(response)

    def test_profile_view(self):
        """Tests the user info view and makes sure auth token is present there"""
        self.temporary_login(self.user['login_id'])
        response = self.client.get(url_for('profile.info', user_name=self.user['musicbrainz_id']))
        self.assertTemplateUsed('profile/info.html')
        self.assert200(response)
        self.assertIn(self.user['auth_token'], response.data.decode('utf-8'))

    def test_reset_import_timestamp(self):
        self.temporary_login(self.user['login_id'])
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
        self.temporary_login(self.user['login_id'])
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

    @patch('listenbrainz.webserver.views.user.publish_data_to_queue')
    def test_delete(self, mock_publish_data_to_queue):
        self.temporary_login(self.user['login_id'])
        r = self.client.get(url_for('profile.delete'))
        self.assert200(r)

        r = self.client.post(url_for('profile.delete'), data={'token': self.user['auth_token']})
        mock_publish_data_to_queue.assert_called_once()
        self.assertRedirects(r, '/')
        user = db_user.get(self.user['id'])
        self.assertIsNone(user)


    @patch('listenbrainz.webserver.views.profile.spotify.remove_user')
    @patch('listenbrainz.webserver.views.profile.spotify.get_spotify_oauth')
    def test_connect_spotify(self, mock_get_spotify_oauth, mock_remove_user):
        mock_get_spotify_oauth.return_value.get_authorize_url.return_value = 'someurl'
        self.temporary_login(self.user['login_id'])
        r = self.client.get(url_for('profile.connect_spotify'))
        self.assert200(r)

        r = self.client.post(url_for('profile.connect_spotify'), data={'delete': 'yes'})
        self.assert200(r)
        mock_remove_user.assert_called_once_with(self.user['id'])


    @patch('listenbrainz.webserver.views.profile.spotify.get_access_token')
    @patch('listenbrainz.webserver.views.profile.spotify.add_new_user')
    def test_spotify_callback(self, mock_add_new_user, mock_get_access_token):
        mock_get_access_token.return_value = {
            'access_token': 'token',
            'refresh_token': 'refresh',
            'expires_in': 3600,
        }
        self.temporary_login(self.user['login_id'])
        r = self.client.get(url_for('profile.connect_spotify_callback', code='code'))
        self.assertStatus(r, 302)
        mock_get_access_token.assert_called_once_with('code')
        mock_add_new_user.assert_called_once_with(self.user['id'], {
            'access_token': 'token',
            'refresh_token': 'refresh',
            'expires_in': 3600,
        })

        r = self.client.get(url_for('profile.connect_spotify_callback'))
        self.assert400(r)
