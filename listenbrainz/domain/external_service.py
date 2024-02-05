import datetime
from abc import ABC
from typing import Union, Sequence

from data.model.external_service import ExternalServiceType

from listenbrainz.db import external_service_oauth
from listenbrainz.webserver import db_conn


class ExternalService(ABC):
    """ Base class that external music services only allowing streaming should
    implement to integrate with ListenBrainz. """

    def __init__(self, service: ExternalServiceType):
        """
        Args:
            service (data.model.external_service.ExternalServiceType): unique name identifying the service
        """
        self.service = service

    def add_new_user(self, user_id: int, token: dict) -> bool:
        """ Inserts a user for the specific service in the database
        Args:
            user_id: the ListenBrainz row ID of the user
            token: the response from the OAuth API of the services
        Returns:
            whether the user was inserted in the database
        """
        raise NotImplementedError()

    def remove_user(self, user_id: int):
        """ Delete user entry for user with specified ListenBrainz user ID.

        Args:
            user_id (int): the ListenBrainz row ID of the user
        """
        external_service_oauth.delete_token(db_conn, user_id=user_id, service=self.service, remove_import_log=True)

    def get_user(self, user_id: int) -> Union[dict, None]:
        return external_service_oauth.get_token(db_conn, user_id=user_id, service=self.service)

    def user_oauth_token_has_expired(self, user: dict, within_minutes: int = 5) -> bool:
        """Check if a user's oauth token has expired (within a threshold)

        Args:
            user: the result of :py:meth:`~ExternalService.get_user`
            within_minutes: say that the token has expired if it will expire within this
               many minutes

        Returns:
            True if ``user['token_expires']`` is after the current time
        """
        if within_minutes < 0:
            raise ValueError("within_minutes must be 0 or greater")
        now = datetime.datetime.now(datetime.timezone.utc)
        return user['token_expires'] < (now + datetime.timedelta(minutes=within_minutes))

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


class ExternalServiceAPIError(ExternalServiceError):
    """ Raised in case of api errors from external services. """
    pass


class ExternalServiceInvalidGrantError(ExternalServiceAPIError):
    """ Raised if the external music services' API returns invalid_grant during authorization.
    This usually means that the user has revoked authorization to the ListenBrainz application
    through external means without unlinking the account from ListenBrainz.
    """
    pass
