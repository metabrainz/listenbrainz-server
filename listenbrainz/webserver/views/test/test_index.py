from unittest import mock
from unittest.mock import MagicMock

import ujson
from flask import url_for
from flask_login import login_required
from requests.exceptions import HTTPError
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

import listenbrainz.db.user as db_user
import listenbrainz.webserver.login
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver import create_web_app
from listenbrainz.webserver.testing import ServerTestCase


class IndexViewsTestCase(ServerTestCase, DatabaseTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def test_index(self):
        resp = self.client.get(url_for('index.index'))
        self.assert200(resp)

    def test_downloads(self):
        resp = self.client.get(url_for('index.downloads'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.location, url_for('index.data'))

    def test_data(self):
        resp = self.client.get(url_for('index.data'))
        self.assert200(resp)

    def test_about(self):
        resp = self.client.get(url_for('index.about'))
        self.assert200(resp)

    def test_terms_of_service(self):
        resp = self.client.get(url_for('index.terms_of_service'))
        self.assert200(resp)

    def test_add_data_info(self):
        resp = self.client.get(url_for('index.add_data_info'))
        self.assert200(resp)

    def test_import_data_info(self):
        resp = self.client.get(url_for('index.import_data_info'))
        self.assert200(resp)

    def test_404(self):
        resp = self.client.get('/canyoufindthis')
        self.assert404(resp)
        self.assertIn('Not Found', resp.data.decode('utf-8'))

    def test_lastfm_proxy(self):
        resp = self.client.get(url_for('index.proxy'))
        self.assert200(resp)

    def test_flask_debugtoolbar(self):
        """ Test if flask debugtoolbar is loaded correctly

        Creating an app with default config so that debug is True
        and SECRET_KEY is defined.
        """
        app = create_web_app()
        resp = app.test_client().get('/data/')
        self.assert200(resp)
        self.assertIn('flDebug', str(resp.data))

    def test_current_status(self):
        resp = self.client.get(url_for('index.current_status'))
        self.assert200(resp)

    @mock.patch('listenbrainz.db.user.get')
    def test_menu_not_logged_in(self, mock_user_get):
        resp = self.client.get(url_for('index.index'))
        data = resp.data.decode('utf-8')
        self.assertIn('Sign in', data)
        self.assertIn('Import', data)
        # item in user menu doesn't exist
        self.assertNotIn('Home', data)
        mock_user_get.assert_not_called()

    @mock.patch('listenbrainz.db.user.get_by_login_id')
    def test_menu_logged_in(self, mock_user_get):
        """ If the user is logged in, check that we perform a database query to get user data """
        user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        user = db_user.get_or_create(1, 'iliekcomputers')

        mock_user_get.return_value = user
        self.temporary_login(user['login_id'])
        resp = self.client.get(url_for('index.index'))
        data = resp.data.decode('utf-8')

        # username (menu header)
        self.assertIn('iliekcomputers', data)
        self.assertIn('Import', data)
        # item in user menu

        self.assertIn('Home', data)
        mock_user_get.assert_called_with(user['login_id'])

    @mock.patch('listenbrainz.db.user.get_by_login_id')
    def test_menu_logged_in_error_show(self, mock_user_get):
        """ If the user is logged in, if we show a 400 or 404 error, show the user menu"""
        @self.app.route('/page_that_returns_400')
        def view400():
            raise BadRequest('bad request')

        @self.app.route('/page_that_returns_404')
        def view404():
            raise NotFound('not found')

        user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        user = db_user.get_or_create(1, 'iliekcomputers')
        mock_user_get.return_value = user
        self.temporary_login(user['login_id'])
        resp = self.client.get('/page_that_returns_400')
        data = resp.data.decode('utf-8')
        self.assert400(resp)

        # username (menu header)
        self.assertIn('iliekcomputers', data)
        self.assertIn('Import', data)
        # item in user menu

        self.assertIn('Home', data)
        mock_user_get.assert_called_with(user['login_id'])

        resp = self.client.get('/page_that_returns_404')
        data = resp.data.decode('utf-8')
        self.assert404(resp)
        # username (menu header)
        self.assertIn('iliekcomputers', data)
        self.assertIn('Import', data)
        # item in user menu

        self.assertIn('Home', data)
        mock_user_get.assert_called_with(user['login_id'])

    @mock.patch('listenbrainz.db.user.get')
    def test_menu_logged_in_error_dont_show_no_user(self, mock_user_get):
        """ If the user is logged in, if we show a 500 error, do not show the user menu
            Don't query the database to get a current_user for the template context"""
        @self.app.route('/page_that_returns_500')
        def view500():
            raise InternalServerError('error')

        user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        user = db_user.get_or_create(1, 'iliekcomputers')
        mock_user_get.return_value = user
        self.temporary_login(user['login_id'])
        resp = self.client.get('/page_that_returns_500')
        data = resp.data.decode('utf-8')
        # item not in user menu
        self.assertNotIn('Home', data)
        self.assertNotIn('Sign in', data)
        self.assertIn('Import', data)

    @mock.patch('listenbrainz.db.user.get_by_login_id')
    def test_menu_logged_in_error_dont_show_user_loaded(self, mock_user_get):
        """ If the user is logged in, if we show a 500 error, do not show the user menu
        If the user has previously been loaded in the view, check that it's not
        loaded while rendering the template"""

        user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        user = db_user.get_or_create(1, 'iliekcomputers')

        mock_user_get.return_value = user

        @self.app.route('/page_that_returns_500')
        @login_required
        def view500():
            # flask-login user is loaded during @login_required, so check that the db has been queried
            mock_user_get.assert_called_with(user['login_id'])
            raise InternalServerError('error')

        self.temporary_login(user['login_id'])
        resp = self.client.get('/page_that_returns_500')
        data = resp.data.decode('utf-8')
        self.assertIn('Import', data)
        # item not in user menu
        self.assertNotIn('Home', data)
        self.assertNotIn('Sign in', data)
        # Even after rendering the template, the database has only been queried once (before the exception)
        mock_user_get.assert_called_once()
        self.assertIsInstance(self.get_context_variable('current_user'), listenbrainz.webserver.login.User)

    @mock.patch('listenbrainz.webserver.views.index._authorize_mb_user_deleter')
    @mock.patch('listenbrainz.webserver.views.index.delete_user')
    def test_mb_user_deleter_valid_account(self, mock_delete_user, mock_authorize_mb_user_deleter):
        user_id = db_user.create(1, 'iliekcomputers')
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assert200(r)
        mock_authorize_mb_user_deleter.assert_called_once_with('132')
        mock_delete_user.assert_called_once_with(user_id)

    @mock.patch('listenbrainz.webserver.views.index._authorize_mb_user_deleter')
    @mock.patch('listenbrainz.webserver.views.index.delete_user')
    def test_mb_user_deleter_not_found(self, mock_delete_user, mock_authorize_mb_user_deleter):
        # no user in the db with musicbrainz_row_id = 2
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=2, access_token='312421'))
        self.assert404(r)
        mock_authorize_mb_user_deleter.assert_called_with('312421')
        mock_delete_user.assert_not_called()

    @mock.patch('listenbrainz.webserver.views.index.requests.get')
    @mock.patch('listenbrainz.webserver.views.index.delete_user')
    def test_mb_user_deleter_valid_access_token(self, mock_delete_user, mock_requests_get):
        mock_requests_get.return_value = MagicMock()
        mock_requests_get.return_value.json.return_value = {
            'sub': 'UserDeleter',
            'metabrainz_user_id': 2007538,
        }
        user_id = db_user.create(1, 'iliekcomputers')
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assert200(r)
        mock_requests_get.assert_called_with(
            'https://musicbrainz.org/oauth2/userinfo',
            headers={'Authorization': 'Bearer 132'},
        )
        mock_delete_user.assert_called_with(user_id)

    @mock.patch('listenbrainz.webserver.views.index.requests.get')
    @mock.patch('listenbrainz.webserver.views.index.delete_user')
    def test_mb_user_deleter_invalid_access_tokens(self, mock_delete_user, mock_requests_get):
        mock_requests_get.return_value = MagicMock()
        mock_requests_get.return_value.json.return_value = {
            'sub': 'UserDeleter',
            'metabrainz_user_id': 2007531, # incorrect musicbrainz row id for UserDeleter
        }
        user_id = db_user.create(1, 'iliekcomputers')
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_delete_user.assert_not_called()

        # no sub value
        mock_requests_get.return_value.json.return_value = {
            'metabrainz_user_id': 2007538,
        }
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_delete_user.assert_not_called()

        # no row id
        mock_requests_get.return_value.json.return_value = {
            'sub': 'UserDeleter',
        }
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_delete_user.assert_not_called()

        # incorrect username
        mock_requests_get.return_value.json.return_value = {
            'sub': 'iliekcomputers',
            'metabrainz_user_id': 2007538
        }
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_delete_user.assert_not_called()

        # everything incorrect
        mock_requests_get.return_value.json.return_value = {
            'sub': 'iliekcomputers',
            'metabrainz_user_id': 1,
        }
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_delete_user.assert_not_called()

        # HTTPError while getting userinfo from MusicBrainz
        mock_requests_get.return_value.raise_for_status.side_effect = HTTPError
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_delete_user.assert_not_called()

    def test_recent_listens_page(self):
        response = self.client.get(url_for('index.recent_listens'))
        self.assert200(response)
        self.assertTemplateUsed('index/recent.html')

    def test_feed_page(self):
        user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        self.temporary_login(user['login_id'])
        r = self.client.get('/feed/')
        self.assert200(r)

    def test_similar_users(self):
        resp = self.client.get(url_for('index.similar_users'))
        self.assert200(resp)

    def test_instant_playlist(self):
        resp = self.client.get(url_for('player.load_instant', recording_mbids="87c94c4b-6aed-41a3-bbbd-aa9cd2154c5e"))
        self.assert200(resp)

    def test_release_playlist(self):
        resp = self.client.get(url_for('player.load_release', release_mbid="87c94c4b-6aed-41a3-bbbd-aa9cd2154c5e"))
        self.assert200(resp)
