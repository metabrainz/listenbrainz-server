from flask import current_app

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.audioscrobbler import AudioscrobblerService


class LastfmService(AudioscrobblerService):

    def __init__(self):
        super().__init__(
            ExternalServiceType.LASTFM,
            api_url=current_app.config["LASTFM_API_URL"],
            api_key=current_app.config["LASTFM_API_KEY"],
        )

