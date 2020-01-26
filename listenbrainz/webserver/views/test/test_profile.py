import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.db.spotify as db_spotify
import pytz
import time
import ujson

from datetime import datetime
from flask import url_for
from listenbrainz.domain import spotify
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listen import Listen
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

    def test_spotify_refresh_token_logged_out(self):
        r = self.client.post(url_for('profile.refresh_spotify_token'))
        self.assert401(r)

    def test_spotify_refresh_token_no_token(self):
        self.temporary_login(self.user['login_id'])
        r = self.client.post(url_for('profile.refresh_spotify_token'))
        self.assert404(r)

    @patch('listenbrainz.webserver.views.profile.spotify.get_user')
    @patch('listenbrainz.webserver.views.profile.spotify.refresh_user_token')
    def test_spotify_refresh_token_which_has_expired(self, mock_refresh_user_token, mock_get_user):
        self.temporary_login(self.user['login_id'])
        # token hasn't expired
        expires = datetime.utcfromtimestamp(int(time.time()) + 10).replace(tzinfo=pytz.UTC)
        mock_get_user.return_value = spotify.Spotify(
            user_id=self.user['id'],
            musicbrainz_id=self.user['musicbrainz_id'],
            musicbrainz_row_id=self.user['musicbrainz_row_id'],
            user_token='old-token',
            token_expires=expires, # token hasn't expired
            refresh_token='old-refresh-token',
            last_updated=None,
            record_listens=True,
            error_message=None,
            latest_listened_at=None,
            permission='user-read-recently-played some-other-permission',
        )
        r = self.client.post(url_for('profile.refresh_spotify_token'))
        self.assert200(r)
        mock_refresh_user_token.assert_not_called()
        self.assertDictEqual(r.json, {
            'id': self.user['id'],
            'musicbrainz_id': self.user['musicbrainz_id'],
            'user_token': 'old-token',
            'permission': 'user-read-recently-played some-other-permission',
        })


    @patch('listenbrainz.webserver.views.profile.spotify.get_user')
    @patch('listenbrainz.webserver.views.profile.spotify.refresh_user_token')
    def test_spotify_refresh_token_which_has_not_expired(self, mock_refresh_user_token, mock_get_user):
        self.temporary_login(self.user['login_id'])
        # token hasn't expired
        expires = datetime.utcfromtimestamp(int(time.time()) - 10).replace(tzinfo=pytz.UTC)
        spotify_user = spotify.Spotify(
            user_id=self.user['id'],
            musicbrainz_id=self.user['musicbrainz_id'],
            musicbrainz_row_id=self.user['musicbrainz_row_id'],
            user_token='old-token',
            token_expires=expires, # token has expired
            refresh_token='old-refresh-token',
            last_updated=None,
            record_listens=True,
            error_message=None,
            latest_listened_at=None,
            permission='user-read-recently-played',
        )
        mock_get_user.return_value = spotify_user
        spotify_user.user_token = 'new-token'
        mock_refresh_user_token.return_value = spotify_user
        r = self.client.post(url_for('profile.refresh_spotify_token'))
        self.assert200(r)
        mock_refresh_user_token.assert_called_once()
        self.assertDictEqual(r.json, {
            'id': self.user['id'],
            'musicbrainz_id': self.user['musicbrainz_id'],
            'user_token': 'new-token',
            'permission': 'user-read-recently-played',
        })

    @patch('listenbrainz.listenstore.influx_listenstore.InfluxListenStore.fetch_listens')
    def test_export_streaming(self, mock_fetch_listens):
        self.temporary_login(self.user['login_id'])

        # Three example listens, with only basic data for the purpose of this test.
        # In each listen, one of {release_artist, release_msid, recording_msid}
        # is missing.
        listens = [
            Listen(
                timestamp=1539509881,
                artist_msid='61746abb-76a5-465d-aee7-c4c42d61b7c4',
                recording_msid='6c617681-281e-4dae-af59-8e00f93c4376',
                data={
                    'artist_name': 'Massive Attack',
                    'track_name': 'The Spoils',
                    'additional_info': {},
                },
            ),
            Listen(
                timestamp=1539441702,
                release_msid='0c1d2dc3-3704-4e75-92f9-940801a1eebd',
                recording_msid='7ad53fd7-5b40-4e13-b680-52716fb86d5f',
                data={
                    'artist_name': 'Snow Patrol',
                    'track_name': 'Lifening',
                    'additional_info': {},
                },
            ),
            Listen(
                timestamp=1539441531,
                release_msid='7816411a-2cc6-4e43-b7a1-60ad093c2c31',
                artist_msid='7e2c6fe4-3e3f-496e-961d-dce04a44f01b',
                data={
                    'artist_name': 'Muse',
                    'track_name': 'Drones',
                    'additional_info': {},
                },
            ),
        ]

        # We expect three calls to fetch_listens, and we return two, one, and
        # zero listens in the batch. This tests that we fetch all batches.
        mock_fetch_listens.side_effect = [listens[0:2], listens[2:3], []]

        r = self.client.post(url_for('profile.export_data'))
        self.assert200(r)

        # r.json returns None, so we decode the response manually.
        results = ujson.loads(r.data.decode('utf-8'))

        self.assertDictEqual(results[0], {
            'listened_at': 1539509881,
            'recording_msid': '6c617681-281e-4dae-af59-8e00f93c4376',
            'user_name': None,
            'track_metadata': {
                'artist_name': 'Massive Attack',
                'track_name': 'The Spoils',
                'additional_info': {
                    'artist_msid': '61746abb-76a5-465d-aee7-c4c42d61b7c4',
                    'release_msid': None,
                },
            },
        })
        self.assertDictEqual(results[1], {
            'listened_at': 1539441702,
            'recording_msid': '7ad53fd7-5b40-4e13-b680-52716fb86d5f',
            'user_name': None,
            'track_metadata': {
                'artist_name': 'Snow Patrol',
                'track_name': 'Lifening',
                'additional_info': {
                    'artist_msid': None,
                    'release_msid': '0c1d2dc3-3704-4e75-92f9-940801a1eebd',
                },
            },
        })
        self.assertDictEqual(results[2], {
            'listened_at': 1539441531,
            'recording_msid': None,
            'user_name': None,
            'track_metadata': {
                'artist_name': 'Muse',
                'track_name': 'Drones',
                'additional_info': {
                    'artist_msid': '7e2c6fe4-3e3f-496e-961d-dce04a44f01b',
                    'release_msid': '7816411a-2cc6-4e43-b7a1-60ad093c2c31',
                },
            },
        })
