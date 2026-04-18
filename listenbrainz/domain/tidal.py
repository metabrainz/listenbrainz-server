import hashlib
import base64
import secrets

from flask import current_app, session
from requests_oauthlib import OAuth2Session

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.brainz_service import BaseBrainzService

TIDAL_AUTHORIZE_URL = "https://login.tidal.com/oauth2/authorize"
TIDAL_TOKEN_URL = "https://auth.tidal.com/v1/oauth2/token"
TIDAL_SCOPES = ["r_usr"]


class TidalService(BaseBrainzService):

    def __init__(self):
        super(TidalService, self).__init__(
            ExternalServiceType.TIDAL,
            client_id=current_app.config["TIDAL_CLIENT_ID"],
            client_secret=current_app.config["TIDAL_CLIENT_SECRET"],
            redirect_uri=current_app.config["TIDAL_REDIRECT_URI"],
            authorize_url=TIDAL_AUTHORIZE_URL,
            token_url=TIDAL_TOKEN_URL,
            scopes=TIDAL_SCOPES
        )

    def get_authorize_url(self, scopes: list, state: str = None, **kwargs):
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b'=').decode()
        session["tidal_code_verifier"] = code_verifier
        return super().get_authorize_url(
            scopes, state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256"
        )

    def fetch_access_token(self, code: str):
        code_verifier = session.pop("tidal_code_verifier", None)
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri
        )
        return oauth.fetch_token(
            self.token_url,
            client_secret=self.client_secret,
            code=code,
            include_client_id=True,
            code_verifier=code_verifier
        )
