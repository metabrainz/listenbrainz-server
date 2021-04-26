from abc import ABC

from listenbrainz.domain.external_service import ExternalService


class ImporterService(ExternalService, ABC):

    def get_active_users_to_process(self):
        raise NotImplementedError()

    def update_user_import_status(self, user_id: int, error: str = None):
        raise NotImplementedError()

    def update_latest_listen_ts(self, user_id: int, timestamp):
        raise NotImplementedError()
