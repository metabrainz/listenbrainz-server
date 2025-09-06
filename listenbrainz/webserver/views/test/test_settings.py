from datetime import datetime, timezone

import requests_mock
import spotipy

import listenbrainz.db.user as db_user
import time

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.external_service import ExternalServiceInvalidGrantError
from listenbrainz.domain.spotify import SpotifyService, OAUTH_TOKEN_URL
from listenbrainz.tests.integration import IntegrationTestCase
from unittest.mock import patch
from listenbrainz.db import external_service_oauth as db_oauth, listens_importer


class SettingsViewsTestCase(IntegrationTestCase):

    def setUp(self):
        super(SettingsViewsTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.db_conn, self.user['musicbrainz_id'])
        self.weirduser = db_user.get_or_create(self.db_conn, 2, 'weird\\user name')
        db_user.agree_to_gdpr(self.db_conn, self.weirduser['musicbrainz_id'])
        with self.app.app_context():
            self.service = SpotifyService()

    def test_settings_view(self):
        """Tests the user info view and makes sure auth token is present there"""
        self.temporary_login(self.user['login_id'])
        response = self.client.get(self.custom_url_for('settings.index', path=''))
        self.assertTemplateUsed('index.html')
        self.assert200(response)
        self.assertIn(self.user['auth_token'], response.data.decode('utf-8'))

    def test_reset_import_timestamp(self):
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.music_services_connect', service_name='lastfm'),
            json={"external_user_id": "lucifer"}
        )
        self.assert200(response)
        users = listens_importer.get_active_users_to_process(self.db_conn, ExternalServiceType.LASTFM)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["external_user_id"], "lucifer")
        self.assertEqual(users[0]["latest_listened_at"], None)

        dt_now = datetime.now(tz=timezone.utc)
        response = self.client.post(
            self.custom_url_for('settings.music_services_connect', service_name='lastfm'),
            json={"external_user_id": "lucifer", "latest_listened_at": dt_now.isoformat()}
        )
        self.assert200(response)

        users = listens_importer.get_active_users_to_process(self.db_conn, ExternalServiceType.LASTFM)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["external_user_id"], "lucifer")
        self.assertEqual(users[0]["latest_listened_at"], dt_now)

    def test_user_info_not_logged_in(self):
        """Tests user info view when not logged in"""
        profile_info_url = self.custom_url_for('settings.index', path='')
        response = self.client.get(profile_info_url)
        self.assertRedirects(response, self.custom_url_for('login.index', next=profile_info_url))

    def test_delete_listens(self):
        """Tests delete listens end point"""
        self.temporary_login(self.user['login_id'])
        delete_listens_url = self.custom_url_for('settings.index', path='delete-listens')
        response = self.client.get(delete_listens_url)
        self.assert200(response)

        response = self.client.post(delete_listens_url)
        self.assertDictEqual(response.json, {'success': True})

    def test_delete_listens_not_logged_in(self):
        """Tests delete listens view when not logged in"""
        delete_listens_url = self.custom_url_for('settings.index', path='delete-listens')
        response = self.client.get(delete_listens_url)
        self.assertRedirects(response, self.custom_url_for('login.index', next=delete_listens_url))

        response = self.client.post(delete_listens_url)
        self.assert401(response)

    def test_select_timezone(self):
        """Tests select timezone end point"""
        self.temporary_login(self.user['login_id'])
        select_timezone_url = self.custom_url_for('settings.index', path='select_timezone')
        response = self.client.get(select_timezone_url)
        self.assert200(response)

    def test_select_timezone_logged_out(self):
        """Tests select timezone view when not logged in"""
        select_timezone_url = self.custom_url_for('settings.index', path='select_timezone')
        response = self.client.get(select_timezone_url)
        self.assertStatus(response, 302)
        self.assertRedirects(response, self.custom_url_for('login.index', next=select_timezone_url))

    def test_music_services_details(self):
        self.temporary_login(self.user['login_id'])
        r = self.client.get(self.custom_url_for('settings.index', path='music-services/details'))
        self.assert200(r)

        r = self.client.post(self.custom_url_for('settings.music_services_disconnect', service_name='spotify'), json={})
        self.assertStatus(r, 200)

        with self.app.app_context():
            self.assertIsNone(self.service.get_user(self.user['id']))

    @patch('listenbrainz.domain.spotify.SpotifyService.fetch_access_token')
    @patch.object(spotipy.Spotify, 'current_user')
    def test_spotify_callback(self, mock_current_user, mock_fetch_access_token):
        mock_current_user.return_value = {"id": "test-id"}
        mock_fetch_access_token.return_value = {
            'access_token': 'token',
            'refresh_token': 'refresh',
            'expires_in': 3600,
            'scope': '',
        }
        self.temporary_login(self.user['login_id'])

        r = self.client.get(self.custom_url_for('settings.music_services_callback', service_name='spotify', code='code'))

        self.assertStatus(r, 302)
        mock_fetch_access_token.assert_called_once_with('code')

        with self.app.app_context():
            user = self.service.get_user(self.user['id'])
        self.assertEqual(self.user['id'], user['user_id'])
        self.assertEqual('token', user['access_token'])
        self.assertEqual('refresh', user['refresh_token'])

        r = self.client.get(self.custom_url_for('settings.music_services_callback', service_name='spotify'))
        self.assert400(r)

    def test_spotify_refresh_token_logged_out(self):
        r = self.client.post(self.custom_url_for('settings.refresh_service_token', service_name='spotify'))
        self.assert401(r)

    def test_spotify_refresh_token_no_token(self):
        self.temporary_login(self.user['login_id'])
        r = self.client.post(self.custom_url_for('settings.refresh_service_token', service_name='spotify'))
        self.assert404(r)

    def _create_spotify_user(self, expired):
        offset = -1000 if expired else 1000
        expires = int(time.time()) + offset
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='old-token', refresh_token='old-refresh-token',
                            token_expires_ts=expires, record_listens=False,
                            scopes=['user-read-recently-played', 'some-other-permission'])

    @patch('listenbrainz.domain.spotify.SpotifyService.refresh_access_token')
    def test_spotify_refresh_token_which_has_not_expired(self, mock_refresh_access_token):
        self.temporary_login(self.user['login_id'])
        self._create_spotify_user(expired=False)

        r = self.client.post(self.custom_url_for('settings.refresh_service_token', service_name='spotify'))

        self.assert200(r)
        mock_refresh_access_token.assert_not_called()
        self.assertDictEqual(r.json, {'access_token': 'old-token'})

    @requests_mock.Mocker()
    def test_spotify_refresh_token_which_has_expired(self, mock_requests):
        self.temporary_login(self.user['login_id'])
        self._create_spotify_user(expired=True)
        mock_requests.post(OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'new-token',
            'refresh_token': 'refreshtokentoken',
            'expires_in': 3600,
            'scope': 'user-read-recently-played some-other-permission',
        })

        r = self.client.post(self.custom_url_for('settings.refresh_service_token', service_name='spotify'))

        self.assert200(r)
        self.assertDictEqual(r.json, {'access_token': 'new-token'})

    @patch('listenbrainz.domain.spotify.SpotifyService.refresh_access_token')
    def test_spotify_refresh_token_which_has_been_revoked(self, mock_refresh_user_token):
        self.temporary_login(self.user['login_id'])
        self._create_spotify_user(expired=True)
        mock_refresh_user_token.side_effect = ExternalServiceInvalidGrantError

        response = self.client.post(self.custom_url_for('settings.refresh_service_token', service_name='spotify'))

        self.assertEqual(response.json, {'code': 403, 'error': 'User has revoked authorization to Spotify'})

    # Funkwhale tests
    def _create_funkwhale_user(self):
        """Helper to create a Funkwhale user with token"""
        import listenbrainz.db.funkwhale as db_funkwhale
        from datetime import datetime, timezone
        import time
        
        self.host_url = 'https://demo.funkwhale.audio'
        server_id = db_funkwhale.get_or_create_server(
            self.db_conn, self.host_url, 'client_id', 'client_secret', 'read'
        )
        expires_at = int(time.time()) + 3600
        token_expiry_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        db_funkwhale.save_token(
            self.db_conn, self.user['id'], server_id, 'access_token', 'refresh_token', token_expiry_datetime
        )
        return server_id

    @patch('listenbrainz.domain.funkwhale.FunkwhaleService.get_authorize_url')
    def test_funkwhale_connect(self, mock_auth):
        """Test Funkwhale connect success"""
        mock_auth.return_value = 'https://demo.funkwhale.audio/api/v1/oauth/authorize?client_id=test'
        
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.music_services_connect', service_name='funkwhale'),
            json={"host_url": "https://demo.funkwhale.audio"}
        )
        self.assert200(response)
        data = response.json
        self.assertEqual(data['status'], 'ok')

    def test_funkwhale_connect_missing_host_url(self):
        """Test Funkwhale connect without host_url"""
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.music_services_connect', service_name='funkwhale'),
            json={}
        )
        self.assert400(response)

    @patch('listenbrainz.domain.funkwhale.FunkwhaleService.fetch_access_token')
    @patch('listenbrainz.domain.funkwhale.FunkwhaleService.add_new_user')
    def test_funkwhale_callback(self, mock_add_user, mock_fetch_token):
        """Test successful Funkwhale OAuth callback"""
        import base64
        test_state = base64.b64encode(b'test_state').decode('utf-8')
        
        mock_fetch_token.return_value = {
            'access_token': 'callback_access_token',
            'refresh_token': 'callback_refresh_token',
            'expires_in': 3600
        }
        mock_add_user.return_value = True
        
        # Create server
        import listenbrainz.db.funkwhale as db_funkwhale
        db_funkwhale.get_or_create_server(
            self.db_conn, 'https://demo.funkwhale.audio', 'client_id', 'client_secret', 'read'
        )
        
        self.temporary_login(self.user['login_id'])
        
        # Mock session within the request context
        with self.client.session_transaction() as sess:
            sess['state'] = test_state
            sess['funkwhale_host_url'] = 'https://demo.funkwhale.audio'
        
        response = self.client.get(
            self.custom_url_for('settings.music_services_callback', service_name='funkwhale'),
            query_string={'code': 'auth_code', 'state': test_state}
        )
        self.assertStatus(response, 302)
        mock_fetch_token.assert_called_once_with('auth_code')
        mock_add_user.assert_called_once()

    @patch('listenbrainz.domain.funkwhale.FunkwhaleService.refresh_access_token')
    @patch('listenbrainz.domain.funkwhale.FunkwhaleService.user_oauth_token_has_expired')
    def test_funkwhale_refresh_token(self, mock_expired, mock_refresh):
        """Test Funkwhale token refresh"""
        self._create_funkwhale_user()
        mock_expired.return_value = True
        mock_refresh.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token'
        }
        
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.refresh_service_token', service_name='funkwhale'),
            json={"host_url": "https://demo.funkwhale.audio"}
        )
        self.assert200(response)
        data = response.json
        self.assertEqual(data['access_token'], 'new_access_token')

    def test_funkwhale_disconnect(self):
        """Test Funkwhale disconnect"""
        self._create_funkwhale_user()
        
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.music_services_disconnect', service_name='funkwhale'),
            json={"action": "disable"}
        )
        self.assert200(response)
        data = response.json
        self.assertEqual(data['status'], 'ok')

    # Navidrome tests
    def _create_navidrome_server(self):
        """Helper to create a Navidrome server"""
        import listenbrainz.db.navidrome as db_navidrome
        return db_navidrome.get_or_create_server(
            self.db_conn, 'https://demo.navidrome.org'
        )

    def _create_navidrome_user_token(self, server_id=None):
        """Helper to create a Navidrome user token"""
        import listenbrainz.db.navidrome as db_navidrome
        from cryptography.fernet import Fernet
        
        # Generate key and encrypt test password
        key = Fernet.generate_key()
        cipher_suite = Fernet(key)
        encrypted_password = cipher_suite.encrypt(b'test_password').decode()
        
        # Save the user token
        return db_navidrome.save_user_token(
            self.db_conn, 
            user_id=self.user['id'], 
            host_url='https://demo.navidrome.org',
            username='test_user', 
            encrypted_password=encrypted_password
        )

    @patch('listenbrainz.domain.navidrome.NavidromeService.connect_user')
    def test_navidrome_connect(self, mock_connect):
        """Test Navidrome connect success"""
        mock_connect.return_value = {
            'success': True,
            'host_url': 'https://demo.navidrome.org',
            'username': 'test_user',
            'server_version': '0.49.3',
            'token_id': 123
        }
        
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.music_services_connect', service_name='navidrome'),
            json={
                "host_url": "https://demo.navidrome.org",
                "username": "test_user",
                "password": "test_password"
            }
        )
        self.assert200(response)
        data = response.json
        self.assertTrue(data['success'])
        self.assertEqual(data['host_url'], 'https://demo.navidrome.org')
        self.assertEqual(data['username'], 'test_user')
        
        # Verify connect_user was called with correct parameters
        mock_connect.assert_called_once_with(
            self.user['id'], 
            "https://demo.navidrome.org", 
            "test_user", 
            "test_password"
        )

    def test_navidrome_connect_missing_host_url(self):
        """Test Navidrome connect without host_url"""
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.music_services_connect', service_name='navidrome'),
            json={"username": "test_user", "password": "test_password"}
        )
        self.assert400(response)

    def test_navidrome_connect_missing_credentials(self):
        """Test Navidrome connect without username/password"""
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.music_services_connect', service_name='navidrome'),
            json={"host_url": "https://demo.navidrome.org"}
        )
        self.assert400(response)

    @patch('listenbrainz.domain.navidrome.NavidromeService.remove_user')
    def test_navidrome_disconnect(self, mock_remove):
        """Test Navidrome disconnect"""
        # Create a user token first
        self._create_navidrome_user_token()
        
        self.temporary_login(self.user['login_id'])
        response = self.client.post(
            self.custom_url_for('settings.music_services_disconnect', service_name='navidrome'),
            json={"action": "disable"}
        )
        self.assert200(response)
        data = response.json
        self.assertEqual(data['status'], 'ok')
        self.assertIn('Successfully disconnected', data['message'])
        
        mock_remove.assert_called_once_with(self.user['id'])
