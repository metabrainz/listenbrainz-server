from data.model.external_service import ExternalServiceType
from listenbrainz import db, utils
import sqlalchemy


def add_update_error(user_id: int, service: ExternalServiceType, error_message: str):
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


def update_last_updated(user_id: int, service: ExternalServiceType):
    """ Update the last_updated field for the user with specified LB user_id.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.ExternalServiceType): service to declare import was successful
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE listens_importer
               SET last_updated = now()
                 , error_message = NULL
             WHERE user_id = :user_id
               AND service = :service
        """), {
            "user_id": user_id,
            "service": service.value
        })


def update_latest_listened_at(user_id: int, service: ExternalServiceType, timestamp: int):
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
               SET latest_listened_at = :timestamp
             WHERE user_id = :user_id
               AND service = :service
            """), {
                'user_id': user_id,
                'service': service.value,
                'timestamp': utils.unix_timestamp_to_datetime(timestamp),
            })
