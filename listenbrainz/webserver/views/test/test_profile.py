import requests_mock

import listenbrainz.db.user as db_user
import time
import ujson

from flask import url_for

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.external_service import ExternalServiceInvalidGrantError
from listenbrainz.domain.spotify import SpotifyService, OAUTH_TOKEN_URL
from listenbrainz.listen import Listen
from listenbrainz.tests.integration import IntegrationTestCase
from unittest.mock import patch
from listenbrainz.db.model.feedback import Feedback
from listenbrainz.db import external_service_oauth as db_oauth


class ProfileViewsTestCase(IntegrationTestCase):

    def setUp(self):
        super(ProfileViewsTestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])
        self.weirduser = db_user.get_or_create(2, 'weird\\user name')
        db_user.agree_to_gdpr(self.weirduser['musicbrainz_id'])
        self.service = SpotifyService()

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

    def test_delete_listens(self):
        """Tests delete listens end point"""
        self.temporary_login(self.user['login_id'])
        delete_listens_url = url_for('profile.delete_listens')
        response = self.client.get(delete_listens_url)
        self.assert200(response)

        response = self.client.post(delete_listens_url, data={'token': self.user['auth_token']})
        self.assertRedirects(response, url_for('user.profile', user_name=self.user['musicbrainz_id']))

    def test_delete_listens_not_logged_in(self):
        """Tests delete listens view when not logged in"""
        delete_listens_url = url_for('profile.delete_listens')
        response = self.client.get(delete_listens_url) # GET request
        self.assertStatus(response, 302)
        self.assertRedirects(response, url_for('login.index', next=delete_listens_url))

        response = self.client.post(delete_listens_url) # POST request
        self.assertStatus(response, 302)
        self.assertRedirects(response, url_for('login.index', next=delete_listens_url))

    def test_delete_listens_auth_token_not_provided(self):
        """Tests delete listens end point when auth token is missing"""
        self.temporary_login(self.user['login_id'])
        delete_listens_url = url_for('profile.delete_listens')
        response = self.client.get(delete_listens_url)
        self.assert200(response)

        response = self.client.post(delete_listens_url) # auth token is missing
        self.assertStatus(response, 401)

    def test_delete_listens_invalid_auth_token(self):
        """Tests delete listens end point when auth token is invalid"""
        self.temporary_login(self.user['login_id'])
        delete_listens_url = url_for('profile.delete_listens')
        response = self.client.get(delete_listens_url)
        self.assert200(response)
        
        invalid_auth_token = 'invalid-auth-token'
        response = self.client.post(delete_listens_url, data={'token': invalid_auth_token}) # auth token is invalid
        self.assertStatus(response, 401)

    def test_connect_spotify(self):
        self.temporary_login(self.user['login_id'])
        r = self.client.get(url_for('profile.connect_spotify'))
        self.assert200(r)

        r = self.client.post(url_for('profile.connect_spotify'), data={'delete': 'yes'})
        self.assert200(r)

        self.assertIsNone(self.service.get_user(self.user['id']))

    @patch('listenbrainz.domain.spotify.SpotifyService.fetch_access_token')
    def test_spotify_callback(self, mock_fetch_access_token):
        mock_fetch_access_token.return_value = {
            'access_token': 'token',
            'refresh_token': 'refresh',
            'expires_in': 3600,
            'scope': '',
        }
        self.temporary_login(self.user['login_id'])

        r = self.client.get(url_for('profile.connect_spotify_callback', code='code'))

        self.assertStatus(r, 302)
        mock_fetch_access_token.assert_called_once_with('code')

        user = self.service.get_user(self.user['id'])
        self.assertEqual(self.user['id'], user['user_id'])
        self.assertEqual('token', user['access_token'])
        self.assertEqual('refresh', user['refresh_token'])

        r = self.client.get(url_for('profile.connect_spotify_callback'))
        self.assert400(r)

    def test_spotify_refresh_token_logged_out(self):
        r = self.client.post(url_for('profile.refresh_spotify_token'))
        self.assert401(r)

    def test_spotify_refresh_token_no_token(self):
        self.temporary_login(self.user['login_id'])
        r = self.client.post(url_for('profile.refresh_spotify_token'))
        self.assert404(r)

    def _create_spotify_user(self, expired):
        offset = -100 if expired else 100
        expires = int(time.time()) + offset
        db_oauth.save_token(user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='old-token', refresh_token='old-refresh-token',
                            token_expires_ts=expires, record_listens=False,
                            scopes=['user-read-recently-played', 'some-other-permission'])

    @patch('listenbrainz.domain.spotify.SpotifyService.refresh_access_token')
    def test_spotify_refresh_token_which_has_not_expired(self, mock_refresh_access_token):
        self.temporary_login(self.user['login_id'])
        self._create_spotify_user(expired=False)

        r = self.client.post(url_for('profile.refresh_spotify_token'))

        self.assert200(r)
        mock_refresh_access_token.assert_not_called()
        self.assertDictEqual(r.json, {
            'id': self.user['id'],
            'musicbrainz_id': self.user['musicbrainz_id'],
            'user_token': 'old-token',
            'permission': ['user-read-recently-played', 'some-other-permission'],
        })

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

        r = self.client.post(url_for('profile.refresh_spotify_token'))

        self.assert200(r)
        self.assertDictEqual(r.json, {
            'id': self.user['id'],
            'musicbrainz_id': self.user['musicbrainz_id'],
            'user_token': 'new-token',
            'permission': ['user-read-recently-played', 'some-other-permission'],
        })

    @patch('listenbrainz.domain.spotify.SpotifyService.refresh_access_token')
    def test_spotify_refresh_token_which_has_been_revoked(self, mock_refresh_user_token):
        self.temporary_login(self.user['login_id'])
        self._create_spotify_user(expired=True)
        mock_refresh_user_token.side_effect = ExternalServiceInvalidGrantError

        response = self.client.post(url_for('profile.refresh_spotify_token'))

        self.assertEqual(response.json, {'code': 404, 'error': 'User has revoked authorization to Spotify'})

    @patch('listenbrainz.listenstore.timescale_listenstore.TimescaleListenStore.fetch_listens')
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
            'inserted_at': 0,
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
            'inserted_at': 0,
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
            'inserted_at': 0,
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

    @patch('listenbrainz.db.feedback.get_feedback_for_user')
    def test_export_feedback_streaming(self, mock_fetch_feedback):
        self.temporary_login(self.user['login_id'])

        # Three example feedback, with only basic data for the purpose of this test.
        feedback = [
            Feedback(
                recording_msid='6c617681-281e-4dae-af59-8e00f93c4376',
                score=1,
                user_id=1,
            ),
            Feedback(
                recording_msid='7ad53fd7-5b40-4e13-b680-52716fb86d5f',
                score=1,
                user_id=1,
            ),
            Feedback(
                recording_msid='7816411a-2cc6-4e43-b7a1-60ad093c2c31',
                score=-1,
                user_id=1,
            ),
        ]

        # We expect three calls to get_feedback_for_user, and we return two, one, and
        # zero feedback in the batch. This tests that we fetch all batches.
        mock_fetch_feedback.side_effect = [feedback[0:2], feedback[2:3], []]

        r = self.client.post(url_for('profile.export_feedback'))
        self.assert200(r)

        # r.json returns None, so we decode the response manually.
        results = ujson.loads(r.data.decode('utf-8'))

        self.assertDictEqual(results[0], {
            'recording_msid': '6c617681-281e-4dae-af59-8e00f93c4376',
            'score': 1,
            'user_id': None,
            'created': None,
        })
        self.assertDictEqual(results[1], {
            'recording_msid': '7ad53fd7-5b40-4e13-b680-52716fb86d5f',
            'score': 1,
            'user_id': None,
            'created': None,
        })
        self.assertDictEqual(results[2], {
            'recording_msid': '7816411a-2cc6-4e43-b7a1-60ad093c2c31',
            'score': -1,
            'user_id': None,
            'created': None,
        })

    def test_export_feedback_streaming_not_logged_in(self):
        export_feedback_url = url_for('profile.export_feedback')
        response = self.client.post(export_feedback_url)
        self.assertStatus(response, 302)
        self.assertRedirects(response, url_for('login.index', next=export_feedback_url))
