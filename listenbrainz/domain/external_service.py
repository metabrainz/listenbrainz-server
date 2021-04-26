from abc import ABC

from data.model.external_service import ExternalServiceType

from listenbrainz.db import external_service_oauth as db_oauth


class ExternalService(ABC):

    def __init__(self, service: ExternalServiceType):
        self.service = service

    def add_new_user(self, user_id: int, token: dict):
        raise NotImplementedError()

    def remove_user(self, user_id: int):
        """ Delete user entry for user with specified ListenBrainz user ID.

        Args:
            user_id (int): the ListenBrainz row ID of the user
        """
        db_oauth.delete_token(user_id=user_id, service=self.service, stop_import=True)

    def get_user(self, user_id: int):
        raise NotImplementedError()

    def get_authorize_url(self, scopes: list):
        raise NotImplementedError()

    def fetch_access_token(self, code: str):
        raise NotImplementedError()

    def refresh_access_token(self, user_id: int, refresh_token: str):
        raise NotImplementedError()

    def get_user_connection_details(self, user_id: int):
        raise NotImplementedError()


class ExternalServiceInvalidGrantError(Exception):
    """ Raised if spotify API returns invalid_grant during authorization. This usually means that the user has revoked
    authorization to the ListenBrainz application through Spotify UI."""
    pass


class ExternalServiceImporterError(Exception):
    pass


class ExternalServiceListenBrainzError(Exception):
    pass


class ExternalServiceAPIError(Exception):
    pass

