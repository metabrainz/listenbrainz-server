from flask import current_app

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.audioscrobbler import AudioscrobblerService


class LibrefmService(AudioscrobblerService):

    def __init__(self):
        super().__init__(
            ExternalServiceType.LIBREFM,
            api_url=current_app.config["LIBREFM_API_URL"],
            api_key=current_app.config["LIBREFM_API_KEY"],
        )
