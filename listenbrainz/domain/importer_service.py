from abc import ABC
from typing import List

from listenbrainz.domain.external_service import ExternalService
from listenbrainz.db import listens_importer as db_import


class ImporterService(ExternalService, ABC):
    """ Base class that external music services which also allow to import listen history
    to ListenBrainz should implement."""

    def get_active_users_to_process(self) -> List[dict]:
        """ Return list of active users for importing listens. """
        raise NotImplementedError()

    def update_user_import_status(self, user_id: int, error: str = None):
        """ Update the last_update field for user with specified user ID.

        If there was an error, add the error to the db.

        Args:
            user_id (int): the ListenBrainz row ID of the user
            error (str): the user-friendly error message to be displayed.
        """
        if error:
            db_import.add_update_error(user_id, self.service, error)
        else:
            db_import.update_last_updated(user_id, self.service)

    def update_latest_listen_ts(self, user_id: int, timestamp: int):
        """ Update the latest_listened_at field for user with specified ListenBrainz user ID.

        Args:
            user_id (int): the ListenBrainz row ID of the user
            timestamp (int): the unix timestamp of the latest listen imported for the user
        """
        db_import.update_latest_listened_at(user_id, self.service, timestamp)


class ExternalServiceImporterError(Exception):
    pass
