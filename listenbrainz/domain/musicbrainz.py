import requests
from flask import current_app, url_for

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.brainz_service import BaseBrainzService

MUSICBRAINZ_SCOPES = ["tag", "rating", "profile"]


class MusicBrainzService(BaseBrainzService):

    def __init__(self):
        # these are not MB deployments but LB deployments
        from listenbrainz.webserver import deploy_env
        if deploy_env == "test":
            service = ExternalServiceType.MUSICBRAINZ_TEST
        elif deploy_env == "beta":
            service = ExternalServiceType.MUSICBRAINZ_BETA
        else:
            service = ExternalServiceType.MUSICBRAINZ_PROD
        super(MusicBrainzService, self).__init__(
            service=service,
            client_id=current_app.config["OAUTH_CLIENT_ID"],
            client_secret=current_app.config["OAUTH_CLIENT_SECRET"],
            redirect_uri=url_for("login.musicbrainz_post", _external=True),
            authorize_url=current_app.config["OAUTH_AUTHORIZE_URL"],
            token_url=current_app.config["OAUTH_TOKEN_URL"],
            scopes=MUSICBRAINZ_SCOPES
        )

    def get_user_info(self, token: str):
        response = requests.post(
            current_app.config["OAUTH_INTROSPECTION_URL"],
            data={
                "client_id": current_app.config["OAUTH_CLIENT_ID"],
                "client_secret": current_app.config["OAUTH_CLIENT_SECRET"],
                "token": token,
                "token_type_hint": "access_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()
