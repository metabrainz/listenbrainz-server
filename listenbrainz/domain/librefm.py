from data.model.external_service import ExternalServiceType
from listenbrainz.domain.lastfm import BaseLastfmService


class LibrefmService(BaseLastfmService):

    def __init__(self):
        super().__init__(ExternalServiceType.LIBREFM)
