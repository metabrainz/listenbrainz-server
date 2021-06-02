from datetime import timezone

import requests
from requests import RequestException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth

from flask import current_app
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from listenbrainz.domain.external_service import ExternalService, ExternalServiceInvalidGrantError, \
    ExternalServiceAPIError

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


class YoutubeService(ExternalService):

    def __init__(self):
        super(YoutubeService, self).__init__(ExternalServiceType.YOUTUBE)
        self.client_config = current_app.config["YOUTUBE_CONFIG"]
        self.redirect_uri = current_app.config["YOUTUBE_REDIRECT_URI"]

    def add_new_user(self, user_id: int, token: dict):
        external_service_oauth.save_token(user_id=user_id,
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
        try:
            credentials.refresh(Request())
        except RefreshError as error:
            # refresh error has error message as first arg and the actual error response from the api in the second arg
            error_body = error.args[1]
            if "error" in error_body and error_body["error"] == "invalid_grant":
                raise ExternalServiceInvalidGrantError(error_body)

            raise ExternalServiceAPIError("Could not refresh API Token for Youtube user")
        external_service_oauth.update_token(user_id=user_id,
                                            service=self.service,
                                            access_token=credentials.token,
                                            refresh_token=credentials.refresh_token,
                                            expires_at=int(credentials.expiry.replace(tzinfo=timezone.utc).timestamp()))
        return self.get_user(user_id)

    def remove_user(self, user_id: int):
        user = self.get_user(user_id)
        # try to revoke token with Google Auth API otherwise Google will consider the account
        # be still connected and will not send a refresh_token next time the user tries to
        # connect again. if it doesn't succeed proceed normally and just delete from our database
        self._revoke_token(user["access_token"])
        super(YoutubeService, self).remove_user(user_id)

    def _revoke_token(self, access_token):
        """ Revoke the given access_token using Google OAuth Revoke endpoint.
        Args:
            access_token: the token to be revoked
        """
        response = None
        try:
            session = requests.Session()
            session.mount("https://",
                          HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, method_whitelist=["POST"])))
            response = session.post(OAUTH_REVOKE_URL,
                                    params={'token': access_token},
                                    headers={'content-type': 'application/x-www-form-urlencoded'})
            response.raise_for_status()
        except RequestException:
            error_msg = response.text if response else None
            current_app.logger.error("Error while trying to revoke token: %s", error_msg, exc_info=True)

    def get_user_connection_details(self, user_id: int):
        pass
