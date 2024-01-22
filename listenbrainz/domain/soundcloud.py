import requests
from flask import current_app

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
            authorize_url="https://api.soundcloud.com/connect",
            token_url="https://api.soundcloud.com/oauth2/token",
            scopes=SOUNDCLOUD_SCOPES
        )

    def get_user_info(self, token: str):
        response = requests.post(SOUNDCLOUD_USER_INFO_URL, headers={"Authorization": f"OAuth {token}"})
        response.raise_for_status()
        return response.json()
