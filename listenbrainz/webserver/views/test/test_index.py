import ujson
from unittest import mock
from unittest.mock import MagicMock

from flask import url_for
from flask_login import login_required, AnonymousUserMixin
from requests.exceptions import HTTPError
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound
from pika.exceptions import ConnectionClosed, ChannelClosed

import listenbrainz.db.user as db_user
import listenbrainz.webserver.login
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver import create_app
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
        self.assert_redirects(resp, url_for('index.data'))

    def test_data(self):
        resp = self.client.get(url_for('index.data'))
        self.assert200(resp)

    def test_contribute(self):
        resp = self.client.get(url_for('index.contribute'))
        self.assert200(resp)

    def test_goals(self):
        resp = self.client.get(url_for('index.goals'))
        self.assert200(resp)

    def test_faq(self):
        resp = self.client.get(url_for('index.faq'))
        self.assert200(resp)

    def test_api_docs(self):
        resp = self.client.get(url_for('index.api_docs'))
        self.assert200(resp)

    def test_roadmap(self):
        resp = self.client.get(url_for('index.roadmap'))
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
        app = create_app(debug=True)
        client = app.test_client()
        resp = client.get('/data')
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
        self.assertNotIn('My Listens', data)
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

        self.assertIn('My Listens', data)
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

        self.assertIn('My Listens', data)
        mock_user_get.assert_called_with(user['login_id'])

        resp = self.client.get('/page_that_returns_404')
        data = resp.data.decode('utf-8')
        self.assert404(resp)
        # username (menu header)
        self.assertIn('iliekcomputers', data)
        self.assertIn('Import', data)
        # item in user menu

        self.assertIn('My Listens', data)
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
        self.assertNotIn('My Listens', data)
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
        self.assertNotIn('My Listens', data)
        self.assertNotIn('Sign in', data)
        # Even after rendering the template, the database has only been queried once (before the exception)
        mock_user_get.assert_called_once()
        self.assertIsInstance(self.get_context_variable('current_user'), listenbrainz.webserver.login.User)

    @mock.patch('listenbrainz.webserver.views.index._authorize_mb_user_deleter')
    @mock.patch('listenbrainz.webserver.views.index.delete_user')
    def test_mb_user_deleter_valid_account(self, mock_delete_user, mock_authorize_mb_user_deleter):
        user1 = db_user.create(1, 'iliekcomputers')
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assert200(r)
        mock_authorize_mb_user_deleter.assert_called_once_with('132')
        mock_delete_user.assert_called_once_with('iliekcomputers')

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
        user1 = db_user.create(1, 'iliekcomputers')
        r = self.client.get(url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assert200(r)
        mock_requests_get.assert_called_with(
            'https://musicbrainz.org/oauth2/userinfo',
            headers={'Authorization': 'Bearer 132'},
        )
        mock_delete_user.assert_called_with('iliekcomputers')

    @mock.patch('listenbrainz.webserver.views.index.requests.get')
    @mock.patch('listenbrainz.webserver.views.index.delete_user')
    def test_mb_user_deleter_invalid_access_tokens(self, mock_delete_user, mock_requests_get):
        mock_requests_get.return_value = MagicMock()
        mock_requests_get.return_value.json.return_value = {
            'sub': 'UserDeleter',
            'metabrainz_user_id': 2007531, # incorrect musicbrainz row id for UserDeleter
        }
        user1 = db_user.create(1, 'iliekcomputers')
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
        props = ujson.loads(self.get_context_variable('props'))
        self.assertEqual(props['mode'], 'recent')
        self.assertDictEqual(props['spotify'], {})

    def test_feed_page_404s_for_non_devs(self):
        user = db_user.get_or_create(1, 'iamnotadev')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        self.temporary_login(user['login_id'])
        r = self.client.get('/feed')
        self.assert404(r)

    def test_feed_page_200s_for_devs(self):
        user = db_user.get_or_create(1, 'iliekcomputers') # dev
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        self.temporary_login(user['login_id'])
        r = self.client.get('/feed')
        self.assert200(r)
