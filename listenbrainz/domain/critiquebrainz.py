import time
from datetime import timezone

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth

from flask import current_app

from listenbrainz.domain.external_service import ExternalService, ExternalServiceInvalidGrantError

CRITIQUEBRAINZ_SCOPES = ["review"]

OAUTH_AUTHORIZE_URL = "https://critiquebrainz.org/oauth/authorize"
OAUTH_TOKEN_URL = "https://critiquebrainz.org/ws/1/oauth/token"


class CritiqueBrainzService(ExternalService):

    def __init__(self):
        super(CritiqueBrainzService, self).__init__(ExternalServiceType.CRITIQUEBRAINZ)
        self.client_id = current_app.config["CRITIQUEBRAINZ_CLIENT_ID"]
        self.client_secret = current_app.config["CRITIQUEBRAINZ_CLIENT_SECRET"]
        self.redirect_uri = current_app.config["CRITIQUEBRAINZ_REDIRECT_URI"]

    def add_new_user(self, user_id: int, token: dict) -> bool:
        expires_at = int(time.time()) + token['expires_in']
        external_service_oauth.save_token(
            user_id=user_id,
            service=self.service,
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
            token_expires_ts=expires_at,
            record_listens=False,
            scopes=CRITIQUEBRAINZ_SCOPES
        )
        return True

    def get_authorize_url(self, scopes: list):
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=scopes
        )
        authorization_url, _ = oauth.authorization_url(OAUTH_AUTHORIZE_URL)
        return authorization_url

    def fetch_access_token(self, code: str):
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri
        )
        return oauth.fetch_token(
            OAUTH_TOKEN_URL,
            client_secret=self.client_secret,
            code=code,
            include_client_id=True
        )

    def refresh_access_token(self, user_id: int, refresh_token: str):
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri
        )
        try:
            token = oauth.refresh_token(
                OAUTH_TOKEN_URL,
                client_secret=self.client_secret,
                refresh_token=refresh_token
            )
        except InvalidGrantError as e:
            raise ExternalServiceInvalidGrantError("User revoked access") from e

        expires_at = int(time.time()) + token['expires_in']
        external_service_oauth.update_token(
            user_id=user_id,
            service=self.service,
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
            expires_at=expires_at
        )
        return self.get_user(user_id)

    def get_user_connection_details(self, user_id: int):
        pass
