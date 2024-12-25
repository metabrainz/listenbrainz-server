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
