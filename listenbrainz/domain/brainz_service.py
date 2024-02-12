import time

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from listenbrainz.db import external_service_oauth

from listenbrainz.domain.external_service import ExternalService, ExternalServiceInvalidGrantError
from listenbrainz.webserver import db_conn


class BaseBrainzService(ExternalService):

    def __init__(self, service, client_id, client_secret, redirect_uri,
                 authorize_url, token_url, scopes):
        super(BaseBrainzService, self).__init__(service)
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.scopes = scopes

    def add_new_user(self, user_id: int, token: dict) -> bool:
        expires_at = int(time.time()) + token["expires_in"]
        external_service_oauth.save_token(
            db_conn,
            user_id=user_id,
            service=self.service,
            access_token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            token_expires_ts=expires_at,
            record_listens=False,
            scopes=self.scopes
        )
        return True

    def update_user(self, user_id: int, token: dict) -> bool:
        expires_at = int(time.time()) + token["expires_in"]
        external_service_oauth.update_token(
            db_conn,
            user_id=user_id,
            service=self.service,
            access_token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            expires_at=expires_at
        )
        return True

    def get_authorize_url(self, scopes: list, state: str = None, **kwargs):
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=scopes,
            state=state
        )
        authorization_url, _ = oauth.authorization_url(self.authorize_url, **kwargs)
        return authorization_url

    def fetch_access_token(self, code: str):
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri
        )
        return oauth.fetch_token(
            self.token_url,
            client_secret=self.client_secret,
            code=code,
            include_client_id=True
        )

    def refresh_access_token(self, user_id: int, refresh_token: str):
        oauth = OAuth2Session(client_id=self.client_id, redirect_uri=self.redirect_uri)
        try:
            token = oauth.refresh_token(
                self.token_url,
                client_secret=self.client_secret,
                client_id=self.client_id,
                refresh_token=refresh_token,
            )
        except InvalidGrantError as e:
            raise ExternalServiceInvalidGrantError("User revoked access") from e

        expires_at = int(time.time()) + token["expires_in"]
        external_service_oauth.update_token(
            db_conn,
            user_id=user_id,
            service=self.service,
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
            expires_at=expires_at
        )
        return self.get_user(user_id)

    def get_user_connection_details(self, user_id: int):
        pass
