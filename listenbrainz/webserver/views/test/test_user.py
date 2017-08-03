from listenbrainz.webserver.testing import ServerTestCase
from flask import url_for
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
import time

class UserViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create('iliekcomputers')
        self.weirduser = db_user.get_or_create('weird\\user name')

    def test_user_page(self):
        response = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(response)

    def test_scraper_username(self):
        """ Tests that the username is correctly rendered in the last.fm importer """
        response = self.client.get(
            url_for('user.lastfmscraper', user_name=self.user['musicbrainz_id']),
            query_string={
                'user_token': self.user['auth_token'],
                'lastfm_username': 'dummy',
            }
        )
        self.assert200(response)
        self.assertIn('var user_name = "iliekcomputers";', response.data.decode('utf-8'))

        response = self.client.get(
            url_for('user.lastfmscraper', user_name=self.weirduser['musicbrainz_id']),
            query_string={
                'user_token': self.weirduser['auth_token'],
                'lastfm_username': 'dummy',
            }
        )
        self.assert200(response)
        self.assertIn('var user_name = "weird%5Cuser%20name";', response.data.decode('utf-8'))

    def test_reset_import_timestamp_get(self):
        self.temporary_login(self.user['id'])
        response = self.client.get(url_for('user.reset_latest_import_timestamp'))
        self.assertTemplateUsed('user/resetlatestimportts.html')
        self.assert200(response)

    def test_reset_import_timestamp_post(self):
        self.temporary_login(self.user['id'])
        val = int(time.time())
        db_user.update_latest_import(self.user['musicbrainz_id'], val)

        response = self.client.post(
            url_for('user.reset_latest_import_timestamp'),
            data={
                'reset': 'yes',
                'token': self.user['auth_token']
            }
        )
        self.assertStatus(response, 302) # should have redirected to the import page
        self.assertRedirects(response, url_for('user.import_data'))
        ts = db_user.get(self.user['id'])['latest_import'].strftime('%s')
        self.assertEqual(int(ts), 0)

    def test_user_info_view(self):
        """Tests the user info view and makes sure auth token is present there"""
        response = self.client.get(url_for('user.info', user_name=self.user['musicbrainz_id']))
        self.assertTemplateUsed('user/info.html')
        self.assert200(response)
        self.assertIn(self.user['auth_token'], response.data.decode('utf-8'))

    def test_user_info_404(self):
        """Tests 404 for user info view"""
        response = self.client.get(url_for('user.info', user_name='thisuserdoesnotexist'))
        self.assert404(response)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)
