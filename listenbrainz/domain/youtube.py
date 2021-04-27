from datetime import timezone

from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth as db_oauth

from flask import current_app
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from listenbrainz.domain.external_service import ExternalService

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


class YoutubeService(ExternalService):

    def __init__(self):
        super(YoutubeService, self).__init__(ExternalServiceType.YOUTUBE)
        self.client_config = current_app.config["YOUTUBE_CONFIG"]
        self.redirect_uri = current_app.config["YOUTUBE_REDIRECT_URI"]

    def add_new_user(self, user_id: int, token: dict):
        db_oauth.save_token(user_id=user_id,
                            service=self.service,
                            access_token=token["access_token"],
                            refresh_token=token["refresh_token"],
                            token_expires_ts=int(token["expires_at"]),
                            record_listens=False,
                            scopes=token["scope"])

    def get_authorize_url(self, scopes: list):
        flow = Flow.from_client_config(self.client_config,
                                       scopes=scopes,
                                       redirect_uri=self.redirect_uri)

        authorization_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true")
        return authorization_url

    def fetch_access_token(self, code: str):
        flow = Flow.from_client_config(self.client_config,
                                       scopes=YOUTUBE_SCOPES,
                                       redirect_uri=self.redirect_uri)
        return flow.fetch_token(code=code)

    def refresh_access_token(self, user_id: int, refresh_token: str):
        client = self.client_config["web"]
        user = self.get_user(user_id)
        credentials = Credentials(token=user["access_token"],
                                  refresh_token=user["refresh_token"],
                                  client_id=client["client_id"],
                                  client_secret=client["client_secret"],
                                  token_uri=client["token_uri"],
                                  scopes=YOUTUBE_SCOPES,
                                  expiry=user["token_expires"])
        credentials.refresh(Request())
        db_oauth.update_token(user_id=user_id,
                              service=self.service,
                              access_token=credentials.token,
                              refresh_token=credentials.refresh_token,
                              expires_at=int(credentials.expiry.replace(tzinfo=timezone.utc).timestamp()))
        return self.get_user(user_id)

    def get_user_connection_details(self, user_id: int):
        pass
