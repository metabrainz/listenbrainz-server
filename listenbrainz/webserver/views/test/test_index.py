from unittest import mock
from unittest.mock import MagicMock, patch

from flask_login import login_required
from requests.exceptions import HTTPError
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

import listenbrainz.db.user as db_user
import listenbrainz.webserver.login
from listenbrainz.background.background_tasks import get_task
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import create_web_app
from listenbrainz.webserver.testing import ServerAppPerTestTestCase


class IndexViewsTestCase(IntegrationTestCase):

    def test_index(self):
        resp = self.client.get(self.custom_url_for('index.index_pages', page=''))
        self.assert200(resp)

    def test_data(self):
        resp = self.client.get(self.custom_url_for('index.index_pages', path='data'))
        self.assert200(resp)

    def test_about(self):
        resp = self.client.get(self.custom_url_for('index.index_pages', path='about'))
        self.assert200(resp)

    def test_terms_of_service(self):
        resp = self.client.get(self.custom_url_for('index.index_pages', path='terms-of-service'))
        self.assert200(resp)

    def test_add_data_info(self):
        resp = self.client.get(self.custom_url_for('index.index_pages', path='add-data'))
        self.assert200(resp)

    def test_import_data_info(self):
        resp = self.client.get(self.custom_url_for('index.index_pages', path='import-data'))
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
        resp = self.client.get(self.custom_url_for('index.current_status'))
        self.assert200(resp)

    @mock.patch('listenbrainz.db.user.get')
    def test_menu_not_logged_in(self, mock_user_get):
        resp = self.client.post(self.custom_url_for('index.index'))
        self.assert200(resp)
        mock_user_get.assert_not_called()

    @mock.patch('listenbrainz.webserver.views.index._authorize_mb_user_deleter')
    def test_mb_user_deleter_valid_account(self, mock_authorize_mb_user_deleter):
        user_id = db_user.create(self.db_conn, 1, 'iliekcomputers')
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assert200(r)
        mock_authorize_mb_user_deleter.assert_called_once_with('132')
        with self.app.app_context():
            task = get_task()
            self.assertIsNotNone(task)
            self.assertEqual(task.user_id, user_id)
            self.assertEqual(task.task, "delete_user")

    @mock.patch('listenbrainz.webserver.views.index._authorize_mb_user_deleter')
    @mock.patch('listenbrainz.background.background_tasks.add_task')
    def test_mb_user_deleter_not_found(self, mock_add_task, mock_authorize_mb_user_deleter):
        # no user in the db with musicbrainz_row_id = 2
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=2, access_token='312421'))
        self.assert404(r)
        mock_authorize_mb_user_deleter.assert_called_with('312421')
        mock_add_task.assert_not_called()

    @mock.patch.object(MusicBrainzService, "get_user_info")
    def test_mb_user_deleter_valid_access_token(self, mock_get_user_info):
        mock_get_user_info.return_value = {
            'sub': 'UserDeleter',
            'metabrainz_user_id': 2007538,
        }
        user_id = db_user.create(self.db_conn,1, 'iliekcomputers')
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assert200(r)
        mock_get_user_info.assert_called_with('132')
        with self.app.app_context():
            task = get_task()
            self.assertIsNotNone(task)
            self.assertEqual(task.user_id, user_id)
            self.assertEqual(task.task, "delete_user")

    @mock.patch.object(MusicBrainzService, "get_user_info")
    @mock.patch('listenbrainz.background.background_tasks.add_task')
    def test_mb_user_deleter_invalid_access_tokens(self, mock_add_task, mock_get_user_info):
        mock_get_user_info.return_value = {
            'sub': 'UserDeleter',
            'metabrainz_user_id': 2007531, # incorrect musicbrainz row id for UserDeleter
        }
        user_id = db_user.create(self.db_conn,1, 'iliekcomputers')
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_add_task.assert_not_called()

        # no sub value
        mock_get_user_info.return_value = {
            'metabrainz_user_id': 2007538,
        }
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_add_task.assert_not_called()

        # no row id
        mock_get_user_info.return_value = {
            'sub': 'UserDeleter',
        }
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_add_task.assert_not_called()

        # incorrect username
        mock_get_user_info.return_value = {
            'sub': 'iliekcomputers',
            'metabrainz_user_id': 2007538
        }
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_add_task.assert_not_called()

        # everything incorrect
        mock_get_user_info.return_value = {
            'sub': 'iliekcomputers',
            'metabrainz_user_id': 1,
        }
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_add_task.assert_not_called()

        # HTTPError while getting userinfo from MusicBrainz
        mock_get_user_info.side_effect = HTTPError
        r = self.client.get(self.custom_url_for('index.mb_user_deleter', musicbrainz_row_id=1, access_token='132'))
        self.assertStatus(r, 401)
        mock_add_task.assert_not_called()

    def test_recent_listens_page(self):
        response = self.client.get(self.custom_url_for('index.recent_listens'))
        self.assert200(response)
        self.assertTemplateUsed('index.html')

    def test_feed_page(self):
        user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.db_conn, user['musicbrainz_id'])
        self.temporary_login(user['login_id'])
        r = self.client.get('/feed/')
        self.assert200(r)

    @patch("listenbrainz.webserver.views.player.fetch_playlist_recording_metadata")
    def test_instant_playlist(self, mock_recording_metadata):
        resp = self.client.get(self.custom_url_for('player.load_instant', recording_mbids="87c94c4b-6aed-41a3-bbbd-aa9cd2154c5e"))
        self.assert200(resp)

    def test_release_playlist(self):
        resp = self.client.get(self.custom_url_for('player.load_release', release_mbid="87c94c4b-6aed-41a3-bbbd-aa9cd2154c5e"))
        self.assert200(resp)


class IndexViewsTestCase2(ServerAppPerTestTestCase, DatabaseTestCase):

    @classmethod
    def setUpClass(cls):
        ServerAppPerTestTestCase.setUpClass()
        DatabaseTestCase.setUpClass()

    def setUp(self):
        ServerAppPerTestTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        ServerAppPerTestTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    @classmethod
    def tearDownClass(cls):
        ServerAppPerTestTestCase.tearDownClass()
        DatabaseTestCase.tearDownClass()

    @mock.patch('listenbrainz.db.user.get_by_login_id')
    def test_menu_logged_in_error_show(self, mock_user_get):
        """ If the user is logged in, if we show a 400 or 404 error, show the user menu"""

        @self.app.route('/page_that_returns_400')
        def view400():
            raise BadRequest('bad request')

        @self.app.route('/page_that_returns_404')
        def view404():
            raise NotFound('not found')

        user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.db_conn, user['musicbrainz_id'])
        user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        mock_user_get.return_value = user
        self.temporary_login(user['login_id'])
        resp = self.client.get('/page_that_returns_400')
        data = resp.data.decode('utf-8')
        self.assert400(resp)

        mock_user_get.assert_called_with(mock.ANY, user['login_id'])

        resp = self.client.get('/page_that_returns_404')
        data = resp.data.decode('utf-8')
        self.assert404(resp)

        mock_user_get.assert_called_with(mock.ANY, user['login_id'])

    @mock.patch('listenbrainz.db.user.get')
    def test_menu_logged_in_error_dont_show_no_user(self, mock_user_get):
        """ If the user is logged in, if we show a 500 error, do not show the user menu
            Don't query the database to get a current_user for the template context"""

        @self.app.route('/page_that_returns_500')
        def view500():
            raise InternalServerError('error')

        user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.db_conn, user['musicbrainz_id'])
        user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        mock_user_get.return_value = user
        self.temporary_login(user['login_id'])
        resp = self.client.get('/page_that_returns_500')
        data = resp.data.decode('utf-8')
        # no sidenav menu
        self.assertNotIn('Dashboard', data)
        self.assertNotIn('id="side-nav"', data)
        self.assertNotIn('Sign in', data)

    @mock.patch('listenbrainz.db.user.get_by_login_id')
    def test_menu_logged_in_error_dont_show_user_loaded(self, mock_user_get):
        """ If the user is logged in, if we show a 500 error, do not show the user menu
        If the user has previously been loaded in the view, check that it's not
        loaded while rendering the template"""
        self.app.config["TESTING"] = False

        user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.db_conn, user['musicbrainz_id'])
        user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')

        mock_user_get.return_value = user

        @self.app.route('/page_that_returns_500_2')
        @login_required
        def view500_2():
            # flask-login user is loaded during @login_required, so check that the db has been queried
            mock_user_get.assert_called_with(user['login_id'])
            raise InternalServerError('error')

        self.temporary_login(user['login_id'])
        resp = self.client.get('/page_that_returns_500_2')
        data = resp.data.decode('utf-8')
        print(data)

        # no sidenav menu
        self.assertNotIn('Dashboard', data)
        self.assertNotIn('id="side-nav"', data)

        # Even after rendering the template, the database has only been queried once (before the exception)
        mock_user_get.assert_called_once()
        self.assertIsInstance(self.get_context_variable('current_user'), listenbrainz.webserver.login.User)
