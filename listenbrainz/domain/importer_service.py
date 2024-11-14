from abc import ABC
from typing import Union

from flask import current_app

from listenbrainz.domain.external_service import ExternalService, ExternalServiceError
from listenbrainz.db import listens_importer
from listenbrainz.webserver import db_conn


class ImporterService(ExternalService, ABC):
    """ Base class that external music services which also allow to import listen history
    to ListenBrainz should implement."""

    def get_active_users_to_process(self, exclude_error=True) -> list[dict]:
        """ Return list of active users for importing listens. """
        return listens_importer.get_active_users_to_process(db_conn, self.service, exclude_error)

    def update_user_import_status(self, user_id: int, error: str = None):
        """ Update the last_update field for user with specified user ID.

        If there was an error, add the error to the db.

        Args:
            user_id (int): the ListenBrainz row ID of the user
            error (str): the user-friendly error message to be displayed.
        """
        listens_importer.update_import_status(db_conn, user_id, self.service, error)

    def update_latest_listen_ts(self, user_id: int, timestamp: Union[int, float]):
        """ Update the latest_listened_at field for user with specified ListenBrainz user ID.

        Args:
            user_id: the ListenBrainz row ID of the user
            timestamp: the unix timestamp of the latest listen imported for the user
        """
        listens_importer.update_latest_listened_at(db_conn, user_id, self.service, timestamp)


class ExternalServiceImporterError(ExternalServiceError):
    """ Base exception for all errors raised in the listens importer service."""
    pass
