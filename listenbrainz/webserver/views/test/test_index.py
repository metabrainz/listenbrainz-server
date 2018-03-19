from flask import url_for
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver import create_app
from listenbrainz.webserver.testing import ServerTestCase

from unittest import mock


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
        self.assertIn('Import!', data)
        # item in user menu doesn't exist
        self.assertNotIn('Your Listens', data)
        mock_user_get.assert_not_called()

    @mock.patch('listenbrainz.db.user.get')
    def test_menu_logged_in(self, mock_user_get):
        """ If the user is logged in, check that we perform a database query to get user data """
        user = db_user.get_or_create('iliekcomputers')
        mock_user_get.return_value = user
        self.temporary_login(user['id'])
        resp = self.client.get(url_for('index.index'))
        data = resp.data.decode('utf-8')

        # username (menu header)
        self.assertIn('iliekcomputers', data)
        self.assertIn('Import!', data)
        # item in user menu
        self.assertIn('Your Listens', data)
        mock_user_get.assert_called_with(user['id'])

    @mock.patch('listenbrainz.db.user.get')
    def test_menu_logged_in_error_show(self, mock_user_get):
        """ If the user is logged in, if we show a 400 or 404 error, show the user menu"""
        @self.app.route('/page_that_returns_400')
        def view400():
            raise BadRequest('bad request')

        @self.app.route('/page_that_returns_404')
        def view404():
            raise NotFound('not found')

        user = db_user.get_or_create('iliekcomputers')
        mock_user_get.return_value = user
        self.temporary_login(user['id'])
        resp = self.client.get('/page_that_returns_400')
        data = resp.data.decode('utf-8')
        self.assert400(resp)

        # username (menu header)
        self.assertIn('iliekcomputers', data)
        self.assertIn('Import!', data)
        # item in user menu
        self.assertIn('Your Listens', data)
        mock_user_get.assert_called_with(user['id'])

        resp = self.client.get('/page_that_returns_404')
        data = resp.data.decode('utf-8')
        self.assert404(resp)
        # username (menu header)
        self.assertIn('iliekcomputers', data)
        self.assertIn('Import!', data)
        # item in user menu
        self.assertIn('Your Listens', data)
        mock_user_get.assert_called_with(user['id'])

    @mock.patch('listenbrainz.db.user.get')
    def test_menu_logged_in_error_dont_show(self, mock_user_get):
        """ If the user is logged in, if we show a 500 error, do not show the user menu"""
        @self.app.route('/page_that_returns_500')
        def view500():
            raise InternalServerError('error')

        user = db_user.get_or_create('iliekcomputers')
        mock_user_get.return_value = user
        self.temporary_login(user['id'])
        resp = self.client.get('/page_that_returns_500')
        data = resp.data.decode('utf-8')
        # item not in user menu
        self.assertNotIn('Your Listens', data)
        self.assertIn('Sign in', data)
        self.assertIn('Import!', data)
        mock_user_get.assert_not_called()
