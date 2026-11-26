import requests_mock

import listenbrainz.db.user as db_user
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class MusicBrainzServiceTestCase(NonAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user_id = db_user.create(self.db_conn, 212, 'musicbrainz_user')
        with self.app.test_request_context():  # url_for builds the redirect uri
            self.service = MusicBrainzService()

    def token(self, scope):
        return {"access_token": "access-token", "refresh_token": "refresh-token",
                "expires_in": 3600, "token_type": "Bearer", "scope": scope}

    def scopes(self):
        return self.service.get_user(self.user_id)["scopes"]

    def test_stores_granted_scopes(self):
        self.service.add_new_user(self.user_id, self.token(["profile", "email"]))
        self.assertEqual(self.scopes(), ["profile", "email"])

        # an existing user logging in again
        self.service.update_user(self.user_id, self.token(["profile", "synapse:notifications:inbox"]))
        self.assertEqual(self.scopes(), ["profile", "synapse:notifications:inbox"])

    @requests_mock.Mocker()
    def test_refresh_stores_granted_scopes(self, mock_requests):
        self.service.add_new_user(self.user_id, self.token(["profile"]))
        mock_requests.post(self.app.config["OAUTH_TOKEN_URL"],
                           json=self.token("profile synapse:notifications:inbox"))

        self.service.refresh_access_token(self.user_id, "refresh-token")
        self.assertEqual(self.scopes(), ["profile", "synapse:notifications:inbox"])

    def test_without_scope_in_response_stores_requested(self):
        token = self.token(None)
        del token["scope"]
        self.service.add_new_user(self.user_id, token)
        self.assertEqual(self.scopes(), self.service.scopes)
