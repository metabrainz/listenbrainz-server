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


def import_feedback(user_id: int, lfm_user: str):
    """ Import a user's loved tracks from Last.fm into LB feedback table.

    Module-level wrapper kept for backward compatibility with feedback_api.py.
    """
    service = LastfmService()
    return service.import_feedback(user_id, lfm_user)
