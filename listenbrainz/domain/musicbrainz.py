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
            client_id=current_app.config["MUSICBRAINZ_CLIENT_ID"],
            client_secret=current_app.config["MUSICBRAINZ_CLIENT_SECRET"],
            redirect_uri=url_for('login.musicbrainz_post', _external=True),
            authorize_url=f"{current_app.config['MUSICBRAINZ_BASE_URL']}/oauth2/authorize",
            token_url=f"{current_app.config['MUSICBRAINZ_BASE_URL']}/oauth2/token",
            scopes=MUSICBRAINZ_SCOPES
        )

    def get_user_info(self, token: str):
        response = requests.post(
            f"{current_app.config['MUSICBRAINZ_BASE_URL']}/oauth2/userinfo",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
