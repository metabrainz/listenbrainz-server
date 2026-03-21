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

    def update_status(self, user_id: int, state: str, listens_count: int, error_message: str = None, retry: bool = True):
        """ Update import status for the user.

        Args:
            user_id: the ListenBrainz row ID of the user
            state: import state string (e.g. "Importing", "Synced", "Error")
            listens_count: number of listens imported so far
            error_message: user-friendly error message; if set, stored alongside the status
            retry: whether to retry the import on next run (only relevant when error is set)
        """
        listens_importer.update_status(
            db_conn, user_id, self.service, state, listens_count,
            error={"message": error_message, "retry": retry} if error_message else None
        )

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
