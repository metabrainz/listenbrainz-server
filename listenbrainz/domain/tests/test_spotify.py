import spotipy.oauth2
import time

from flask import current_app
from listenbrainz.domain import spotify
from listenbrainz.webserver.testing import ServerTestCase
from unittest import mock
from unittest.mock import MagicMock


class SpotifyDomainTestCase(ServerTestCase):

    def setUp(self):
        super(SpotifyDomainTestCase, self).setUp()
        self.spotify_user = spotify.Spotify(
                user_id=1,
                musicbrainz_id='spotify_user',
                musicbrainz_row_id=312,
                user_token='old-token',
                token_expires=int(time.time()),
                refresh_token='old-refresh-token',
                last_updated=None,
                record_listens=True,
                error_message=None,
                latest_listened_at=None,
                permission='user-read-recently-played',
            )

    def test_none_values_for_last_updated_and_latest_listened_at(self):
        self.assertIsNone(self.spotify_user.last_updated_iso)
        self.assertIsNone(self.spotify_user.latest_listened_at_iso)

    @mock.patch('listenbrainz.domain.spotify.db_spotify.get_user')
    @mock.patch('listenbrainz.domain.spotify.get_spotify_oauth')
    @mock.patch('listenbrainz.domain.spotify.db_spotify.update_token')
    def test_refresh_user_token(self, mock_update_token, mock_get_spotify_oauth, mock_get_user):
        expires_at = int(time.time()) + 3600
        mock_get_spotify_oauth.return_value.refresh_access_token.return_value = {
            'access_token': 'tokentoken',
            'refresh_token': 'refreshtokentoken',
            'expires_at': expires_at,
            'scope': '',
        }

        spotify.refresh_user_token(self.spotify_user)
        mock_update_token.assert_called_with(
            self.spotify_user.user_id,
            'tokentoken',
            'refreshtokentoken',
            expires_at,
        )
        mock_get_user.assert_called_with(self.spotify_user.user_id)

    def test_get_spotify_oauth(self):
        func_oauth = spotify.get_spotify_oauth()
        self.assertEqual(func_oauth.client_id, current_app.config['SPOTIFY_CLIENT_ID'])
        self.assertEqual(func_oauth.client_secret, current_app.config['SPOTIFY_CLIENT_SECRET'])
        self.assertEqual(func_oauth.redirect_uri, 'http://localhost/profile/connect-spotify/callback')
        self.assertIsNone(func_oauth.scope)

        func_oauth = spotify.get_spotify_oauth(spotify.SPOTIFY_LISTEN_PERMISSIONS)
        self.assertIn('streaming', func_oauth.scope)
        self.assertIn('user-read-birthdate', func_oauth.scope)
        self.assertIn('user-read-email', func_oauth.scope)
        self.assertIn('user-read-private', func_oauth.scope)
        self.assertNotIn('user-read-recently-played', func_oauth.scope)
        self.assertNotIn('user-read-currently-playing', func_oauth.scope)

        func_oauth = spotify.get_spotify_oauth(spotify.SPOTIFY_IMPORT_PERMISSIONS)
        self.assertIn('user-read-currently-playing', func_oauth.scope)
        self.assertIn('user-read-recently-played', func_oauth.scope)
        self.assertNotIn('streaming', func_oauth.scope)
        self.assertNotIn('user-read-birthdate', func_oauth.scope)
        self.assertNotIn('user-read-email', func_oauth.scope)
        self.assertNotIn('user-read-private', func_oauth.scope)


    @mock.patch('listenbrainz.domain.spotify.db_spotify.get_user')
    def test_get_user(self, mock_db_get_user):
        t = int(time.time())
        mock_db_get_user.return_value = {
            'user_id': 1,
            'musicbrainz_id': 'spotify_user',
            'musicbrainz_row_id': 312,
            'user_token': 'token-token-token',
            'token_expires': t,
            'refresh_token': 'refresh-refresh-refresh',
            'last_updated': None,
            'record_listens': True,
            'error_message': 'oops',
            'latest_listened_at': None,
            'permission': 'user-read-recently-played',
        }

        user = spotify.get_user(1)
        self.assertIsInstance(user, spotify.Spotify)
        self.assertEqual(user.user_id, 1)
        self.assertEqual(user.musicbrainz_id, 'spotify_user')
        self.assertEqual(user.user_token, 'token-token-token')
        self.assertEqual(user.token_expires, t)
        self.assertEqual(user.last_updated, None)
        self.assertEqual(user.record_listens, True)
        self.assertEqual(user.error_message, 'oops')

    @mock.patch('listenbrainz.domain.spotify.db_spotify.delete_spotify')
    def test_remove_user(self, mock_delete):
        spotify.remove_user(1)
        mock_delete.assert_called_with(1)

    @mock.patch('listenbrainz.domain.spotify.db_spotify.create_spotify')
    @mock.patch('listenbrainz.domain.spotify.time.time')
    def test_add_new_user(self, mock_time, mock_create):
        mock_time.return_value = 0
        spotify.add_new_user(1, {
            'access_token': 'access-token',
            'refresh_token': 'refresh-token',
            'expires_in': 3600,
            'scope': '',
        })
        mock_create.assert_called_with(1, 'access-token', 'refresh-token', 3600, False, '')

    @mock.patch('listenbrainz.domain.spotify.db_spotify.get_active_users_to_process')
    def test_get_active_users(self, mock_get_active_users):
        t = int(time.time())
        mock_get_active_users.return_value = [
            {
                'user_id': 1,
                'musicbrainz_id': 'spotify_user',
                'musicbrainz_row_id': 312,
                'user_token': 'token-token-token',
                'token_expires': t,
                'refresh_token': 'refresh-refresh-refresh',
                'last_updated': None,
                'record_listens': True,
                'error_message': 'oops',
                'latest_listened_at': None,
                'permission': 'user-read-recently-played',
            },
            {
                'user_id': 2,
                'musicbrainz_id': 'spotify_user_2',
                'musicbrainz_row_id': 321,
                'user_token': 'token-token-token321',
                'token_expires': t + 31,
                'refresh_token': 'refresh-refresh-refresh321',
                'last_updated': None,
                'record_listens': True,
                'error_message': 'oops2',
                'latest_listened_at': None,
                'permission': 'user-read-recently-played',
            },
        ]

        lst = spotify.get_active_users_to_process()
        mock_get_active_users.assert_called_once()
        self.assertEqual(len(lst), 2)
        self.assertIsInstance(lst[0], spotify.Spotify)
        self.assertIsInstance(lst[1], spotify.Spotify)
        self.assertEqual(lst[0].user_id, 1)
        self.assertEqual(lst[1].user_id, 2)

    @mock.patch('listenbrainz.domain.spotify.db_spotify.update_latest_listened_at')
    def test_update_latest_listened_at(self, mock_update_listened_at):
        t = int(time.time())
        spotify.update_latest_listened_at(1, t)
        mock_update_listened_at.assert_called_once_with(1, t)

    @mock.patch('listenbrainz.domain.spotify.get_spotify_oauth')
    def test_refresh_user_token_bad(self, mock_get_spotify_oauth):
        mock_oauth = MagicMock()
        mock_oauth.refresh_access_token.return_value = None
        mock_get_spotify_oauth.return_value = mock_oauth

        with self.assertRaises(spotify.SpotifyAPIError):
            spotify.refresh_user_token(self.spotify_user)
