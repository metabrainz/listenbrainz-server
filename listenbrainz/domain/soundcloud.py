import base64
import hashlib
import secrets

import requests
from flask import current_app
from requests_oauthlib import OAuth2Session

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.brainz_service import BaseBrainzService

SOUNDCLOUD_SCOPES = []

SOUNDCLOUD_USER_INFO_URL = "https://api.soundcloud.com/me"


class SoundCloudService(BaseBrainzService):

    def __init__(self):
        super(SoundCloudService, self).__init__(
            ExternalServiceType.SOUNDCLOUD,
            client_id=current_app.config["SOUNDCLOUD_CLIENT_ID"],
            client_secret=current_app.config["SOUNDCLOUD_CLIENT_SECRET"],
            redirect_uri=current_app.config["SOUNDCLOUD_REDIRECT_URI"],
            authorize_url="https://secure.soundcloud.com/authorize",
            token_url="https://secure.soundcloud.com/oauth/token",
            scopes=SOUNDCLOUD_SCOPES
        )

    @staticmethod
    def generate_pkce_pair():
        """Return (code_verifier, code_challenge) for OAuth 2.1 PKCE."""
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).rstrip(b"=").decode('utf-8')
        return code_verifier, code_challenge

    def fetch_access_token(self, code: str, code_verifier: str = None):
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri
        )
        return oauth.fetch_token(
            self.token_url,
            client_secret=self.client_secret,
            code=code,
            code_verifier=code_verifier,
            include_client_id=True
        )

    def get_user_info(self, token: str):
        response = requests.get(SOUNDCLOUD_USER_INFO_URL, headers={"Authorization": f"OAuth {token}"})
        response.raise_for_status()
        return response.json()
