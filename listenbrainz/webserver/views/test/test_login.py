from unittest import mock
from urllib.parse import parse_qs, urlparse

import requests
import requests_mock
from flask import session

import listenbrainz.db.user as db_user
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver.login import provider
from listenbrainz.webserver.testing import ServerTestCase


class LoginViewsTestCase(ServerTestCase):

    def test_login_musicbrainz_redirects(self):
        response = self.client.get(self.custom_url_for('login.musicbrainz'))
        self.assertStatus(response, 302)

        query = parse_qs(urlparse(response.location).query)
        self.assertIn("email", query["scope"][0].split())

    def test_login_musicbrainz_forwards_register_hint_to_oauth_domain(self):
        response = self.client.get(
            self.custom_url_for('login.musicbrainz', login_hint='register')
        )
        self.assertStatus(response, 302)

        parsed_url = urlparse(response.location)
        parsed_authorize_url = urlparse(self.app.config["OAUTH_AUTHORIZE_URL"])
        query = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.scheme, parsed_authorize_url.scheme)
        self.assertEqual(parsed_url.netloc, parsed_authorize_url.netloc)
        self.assertEqual(parsed_url.path, parsed_authorize_url.path)
        self.assertEqual(query["login_hint"], ["register"])
        self.assertIn("email", query["scope"][0].split())

    def test_login_musicbrainz_does_not_forward_unknown_login_hint(self):
        response = self.client.get(
            self.custom_url_for('login.musicbrainz', login_hint='invalid')
        )
        self.assertStatus(response, 302)

        query = parse_qs(urlparse(response.location).query)
        self.assertNotIn("login_hint", query)


class LoginProviderTestCase(IntegrationTestCase):

    def _get_user(self, *, musicbrainz_row_id=123, musicbrainz_id="old-user",
                  user_info=None, user_info_error=None):
        with self.app.test_request_context(), requests_mock.Mocker() as mock_requests:
            service = MusicBrainzService()
            service.get_user = mock.Mock(return_value=None)
            service.add_new_user = mock.Mock()
            service.update_user = mock.Mock()

            mock_requests.post(self.app.config["OAUTH_TOKEN_URL"], json={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600,
                "token_type": "Bearer",
            })
            mock_requests.post(self.app.config["OAUTH_INTROSPECTION_URL"], json={
                "active": True,
                "sub": str(musicbrainz_row_id),
                "username": musicbrainz_id,
            })

            user_info_response = user_info if user_info is not None else {
                "sub": str(musicbrainz_row_id),
            }
            if user_info_error is not None:
                mock_requests.get(self.app.config["OAUTH_USERINFO_URL"], exc=user_info_error)
            else:
                mock_requests.get(self.app.config["OAUTH_USERINFO_URL"], json=user_info_response)

            mock_ts = mock.Mock()
            session["musicbrainz"] = {
                "code": "authorization-code",
            }
            with mock.patch.object(provider, "MusicBrainzService", return_value=service), \
                    mock.patch.object(provider, "ts", mock_ts):
                user = provider.get_user()

            service.oauth_requests = list(mock_requests.request_history)
            service.profile_request = next((
                oauth_request
                for oauth_request in service.oauth_requests
                if oauth_request.url == self.app.config["OAUTH_USERINFO_URL"]
            ), None)

        return user, mock_ts.set_empty_values_for_user, service

    def test_new_user_stores_verified_email(self):
        user, mock_set_empty_values, service = self._get_user(user_info={
            "sub": "123",
            "email": "verified@example.com",
            "email_verified": True,
        })

        self.assertEqual(user["email"], "verified@example.com")
        mock_set_empty_values.assert_called_once_with(user["id"])
        self.assertEqual(
            [(request.method, request.url) for request in service.oauth_requests],
            [
                ("POST", self.app.config["OAUTH_TOKEN_URL"]),
                ("POST", self.app.config["OAUTH_INTROSPECTION_URL"]),
                ("GET", self.app.config["OAUTH_USERINFO_URL"]),
            ],
        )
        self.assertEqual(
            service.profile_request.url,
            self.app.config["OAUTH_USERINFO_URL"],
        )
        self.assertEqual(
            service.profile_request.headers["Authorization"],
            "Bearer access-token",
        )

    def test_user_created_by_webhook_does_not_request_email(self):
        user_id = db_user.create(self.db_conn, 123, "old-user")

        user, mock_set_empty_values, service = self._get_user(user_info={
            "sub": "123",
            "email": "verified@example.com",
            "email_verified": True,
        })

        self.assertEqual(user["id"], user_id)
        self.assertIsNone(user["email"])
        mock_set_empty_values.assert_not_called()
        self.assertIsNone(service.profile_request)

    def test_new_user_does_not_store_unverified_email(self):
        user, _, service = self._get_user(user_info={
            "sub": "123",
            "email": "pending@example.com",
            "email_verified": False,
        })

        self.assertIsNone(user["email"])
        self.assertIsNotNone(service.profile_request)

    def test_new_user_without_email_claims_stores_no_email(self):
        user, _, service = self._get_user(user_info={"sub": "123"})

        self.assertIsNone(user["email"])
        self.assertIsNotNone(service.profile_request)

    def test_existing_user_does_not_request_or_update_email(self):
        user_id = db_user.create(self.db_conn, 123, "old-user", "old@example.com")

        user, _, service = self._get_user(user_info={
            "sub": "123",
            "email": "new@example.com",
            "email_verified": True,
        })

        self.assertEqual(user["id"], user_id)
        self.assertEqual(user["email"], "old@example.com")
        self.assertIsNone(service.profile_request)

    def test_missing_email_claim_preserves_webhook_synced_email(self):
        user_id = db_user.create(self.db_conn, 123, "old-user", "webhook@example.com")

        user, _, _ = self._get_user(user_info={"sub": "123"})

        self.assertEqual(user["id"], user_id)
        self.assertEqual(user["email"], "webhook@example.com")

    def test_new_userinfo_failure_aborts_login(self):
        with self.assertRaises(provider.MusicBrainzAuthSessionError):
            self._get_user(user_info_error=requests.HTTPError("userinfo unavailable"))

        self.assertIsNone(db_user.get_by_mb_row_id(self.db_conn, 123))
