from typing import Union

from data.model.external_service import ExternalServiceType
from listenbrainz import db, utils
import sqlalchemy


def update_import_status(user_id: int, service: ExternalServiceType, error_message: str = None):
    """ Add an error message to be shown to the user, thereby setting the user as inactive.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.ExternalServiceType): service to add error for the user
        error_message (str): the user-friendly error message to be displayed
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE listens_importer
               SET last_updated = now()
                 , error_message = :error_message
             WHERE user_id = :user_id
               AND service = :service
        """), {
            "user_id": user_id,
            "error_message": error_message,
            "service": service.value
        })


def update_latest_listened_at(user_id: int, service: ExternalServiceType, timestamp: Union[int, float]):
    """ Update the timestamp of the last listen imported for the user with
    specified LB user ID.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.ExternalServiceType): service to update latest listen timestamp for
        timestamp (int): the unix timestamp of the latest listen imported for the user
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE listens_importer
               SET last_updated = now()
                 , latest_listened_at = :timestamp
             WHERE user_id = :user_id
               AND service = :service
            """), {
                'user_id': user_id,
                'service': service.value,
                'timestamp': utils.unix_timestamp_to_datetime(timestamp),
            })
