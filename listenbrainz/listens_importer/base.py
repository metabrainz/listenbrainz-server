import abc
import time
from abc import abstractmethod

from brainzutils import metrics
from flask import current_app, render_template
from psycopg2 import DatabaseError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import InternalServerError, ServiceUnavailable

from brainzutils.mail import send_mail

from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.domain.external_service import ExternalServiceError
from listenbrainz.webserver.errors import ListenValidationError
from listenbrainz.webserver.models import SubmitListenUserMetadata
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_IMPORT, insert_payload, validate_listen, \
    LISTEN_TYPE_SINGLE, LISTEN_TYPE_PLAYING_NOW

from listenbrainz.db import user as db_user
import listenbrainz

METRIC_UPDATE_INTERVAL = 60  # seconds


class ListensImporter(abc.ABC):

    def __init__(self, name, user_friendly_name, service):
        self.name = name
        self.user_friendly_name = user_friendly_name
        self.service = service
        # number of listens imported since last metric update was submitted
        self._listens_imported_since_last_update = 0
        self._metric_submission_time = time.monotonic() + METRIC_UPDATE_INTERVAL
        self.exclude_error = True

    def notify_error(self, musicbrainz_id: str, error: str):
        """ Notifies specified user via email about error during Spotify import.

        Args:
            musicbrainz_id: the MusicBrainz ID of the user
            error: a description of the error encountered.
        """
        user_email = db_user.get_by_mb_id(listenbrainz.webserver.db_conn, musicbrainz_id, fetch_email=True)["email"]
        if not user_email:
            return

        link = current_app.config['SERVER_ROOT_URL'] + '/settings/music-services/details/'
        text = render_template('emails/listens_importer_error.txt', error=error, link=link)
        send_mail(
            subject=f'ListenBrainz {self.user_friendly_name} Importer Error',
            text=text,
            recipients=[user_email],
            from_name='ListenBrainz',
            from_addr='noreply@' + current_app.config['MAIL_FROM_DOMAIN'],
        )

    def parse_and_validate_listen_items(self, converter, items):
        """ Converts and validates the listens received from the external service API.

        Args:
            converter: a function to parse the incoming items that returns a tuple of (listen, listen_type)
            items: a list of listen events received from the external

        Returns:
            tuple of (now playing listen, a list of recent listens to submit to ListenBrainz, timestamp of latest listen)
        """
        now_playing_listen = None
        listens = []
        latest_listen_ts = None

        for item in items:
            listen, listen_type = converter(item)

            if listen_type == LISTEN_TYPE_IMPORT and \
                    (latest_listen_ts is None or listen['listened_at'] > latest_listen_ts):
                latest_listen_ts = listen['listened_at']

            try:
                validate_listen(listen, listen_type)
                if listen_type == LISTEN_TYPE_IMPORT or listen_type == LISTEN_TYPE_SINGLE:
                    listens.append(listen)

                # set the first now playing listen to now_playing and ignore the rest
                if listen_type == LISTEN_TYPE_PLAYING_NOW and now_playing_listen is None:
                    now_playing_listen = listen
            except ListenValidationError:
                pass
        return now_playing_listen, listens, latest_listen_ts

    def submit_listens_to_listenbrainz(self, user: dict, listens: list[dict], listen_type=LISTEN_TYPE_IMPORT):
        """ Submit a batch of listens to ListenBrainz

        Args:
            user: the user whose listens are to be submitted, dict should contain
                at least musicbrainz_id and user_id
            listens: a list of listens to be submitted
            listen_type: the type of listen (single, import, playing_now)
        """
        username = user['musicbrainz_id']
        user_metadata = SubmitListenUserMetadata(user_id=user['user_id'], musicbrainz_id=username)
        retries = 10
        while retries >= 0:
            try:
                current_app.logger.debug('Submitting %d listens for user %s', len(listens), username)
                insert_payload(listens, user_metadata, listen_type=listen_type)
                current_app.logger.debug('Submitted!')
                break
            except (InternalServerError, ServiceUnavailable) as e:
                retries -= 1
                current_app.logger.error('ISE while trying to import listens for %s: %s', username, str(e))
                if retries == 0:
                    raise ExternalServiceError('ISE while trying to import listens: %s', str(e))

    @abstractmethod
    def process_one_user(self, user):
        pass

    def process_all_users(self):
        """ Get a batch of users to be processed and import their listens.

        Returns:
            (success, failure) where
                success: the number of users whose plays were successfully imported.
                failure: the number of users for whom we faced errors while importing.
        """
        try:
            users = self.service.get_active_users_to_process(self.exclude_error)
        except DatabaseException as e:
            listenbrainz.webserver.db_conn.rollback()
            current_app.logger.error('Cannot get list of users due to error %s', str(e), exc_info=True)
            return 0, 0

        if not users:
            return 0, 0

        current_app.logger.info('Process %d users...' % len(users))
        success = 0
        failure = 0
        for user in users:
            try:
                if user['is_paused']:
                    continue

                self._listens_imported_since_last_update += self.process_one_user(user)
                success += 1
            except (DatabaseException, DatabaseError, SQLAlchemyError):
                listenbrainz.webserver.db_conn.rollback()
                current_app.logger.error(f'{self.name} could not import listens for user %s:',
                                         user['musicbrainz_id'], exc_info=True)
            except Exception:
                current_app.logger.error(f'{self.name} could not import listens for user %s:',
                                         user['musicbrainz_id'], exc_info=True)
                failure += 1

            if time.monotonic() > self._metric_submission_time:
                self._metric_submission_time += METRIC_UPDATE_INTERVAL
                metrics.set(self.name, imported_listens=self._listens_imported_since_last_update)
                self._listens_imported_since_last_update = 0

        current_app.logger.info('Processed %d users successfully!', success)
        current_app.logger.info('Encountered errors while processing %d users.', failure)
        return success, failure

    def main(self):
        current_app.logger.info(f'{self.name} started...')
        while True:
            t = time.monotonic()
            success, failure = self.process_all_users()
            total_users = success + failure
            if total_users > 0:
                total_time = time.monotonic() - t
                avg_time = total_time / total_users
                metrics.set(self.name,
                            users_processed=total_users,
                            time_to_process_all_users=total_time,
                            time_to_process_one_user=avg_time)
                current_app.logger.info('All %d users in batch have been processed.', total_users)
                current_app.logger.info('Total time taken: %.2f s, average time per user: %.2f s.', total_time,
                                        avg_time)
            time.sleep(10)
