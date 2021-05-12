from abc import ABC
from typing import Union, Sequence

from data.model.external_service import ExternalServiceType

from listenbrainz.db import external_service_oauth


class ExternalService(ABC):
    """ Base class that external music services only allowing streaming should
    implement to integrate with ListenBrainz. """

    def __init__(self, service: ExternalServiceType):
        """
        Args:
            service (data.model.external_service.ExternalServiceType): unique name identifying the service
        """
        self.service = service

    def add_new_user(self, user_id: int, token: dict):
        raise NotImplementedError()

    def remove_user(self, user_id: int):
        """ Delete user entry for user with specified ListenBrainz user ID.

        Args:
            user_id (int): the ListenBrainz row ID of the user
        """
        external_service_oauth.delete_token(user_id=user_id, service=self.service, remove_import_log=True)

    def get_user(self, user_id: int) -> Union[dict, None]:
        return external_service_oauth.get_token(user_id=user_id, service=self.service)

    def get_authorize_url(self, scopes: Sequence[str]):
        raise NotImplementedError()

    def fetch_access_token(self, code: str):
        raise NotImplementedError()

    def refresh_access_token(self, user_id: int, refresh_token: str):
        raise NotImplementedError()

    def get_user_connection_details(self, user_id: int):
        raise NotImplementedError()


class ExternalServiceError(Exception):
    """ Base exception for all errors coming from external service integrations."""
    pass


class ExternalServiceInvalidGrantError(ExternalServiceError):
    """ Raised if the external music services' API returns invalid_grant during authorization.
    This usually means that the user has revoked authorization to the ListenBrainz application
    through external means without unlinking the account from ListenBrainz.
    """
    pass


class ExternalServiceAPIError(ExternalServiceError):
    """ Raised in case of api errors from external services. """
    pass
