import datetime
from typing import Optional, Union

from data.model.external_service import ExternalServiceType
from listenbrainz import utils
import sqlalchemy


def update_import_status(db_conn, user_id: int, service: ExternalServiceType, error_message: str = None):
    """ Add an error message to be shown to the user, thereby setting the user as inactive.

    Args:
        db_conn: database connection
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.ExternalServiceType): service to add error for the user
        error_message (str): the user-friendly error message to be displayed
    """
    db_conn.execute(sqlalchemy.text("""
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
    db_conn.commit()


def update_latest_listened_at(db_conn, user_id: int, service: ExternalServiceType, timestamp: Union[int, float]):
    """ Update the timestamp of the last listen imported for the user with
    specified LB user ID.

    Args:
        db_conn: database connection
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.ExternalServiceType): service to update latest listen timestamp for
        timestamp (int): the unix timestamp of the latest listen imported for the user
    """
    db_conn.execute(sqlalchemy.text("""
        INSERT INTO listens_importer (user_id, service, last_updated, latest_listened_at)
             VALUES (:user_id, :service, now(), :timestamp)
        ON CONFLICT (user_id, service)
          DO UPDATE 
                SET last_updated = now()
                  , latest_listened_at = :timestamp
        """), {
            'user_id': user_id,
            'service': service.value,
            'timestamp': utils.unix_timestamp_to_datetime(timestamp),
        })
    db_conn.commit()


def get_latest_listened_at(db_conn, user_id: int, service: ExternalServiceType) -> Optional[datetime.datetime]:
    """ Returns the timestamp of the last listen imported for the user with
    specified LB user ID from the given service.

    Args:
        db_conn: database connection
        user_id: the ListenBrainz row ID of the user
        service: service to update latest listen timestamp for
    Returns:
        timestamp: the unix timestamp of the latest listen imported for the user
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT latest_listened_at
          FROM listens_importer
         WHERE user_id = :user_id
           AND service = :service
        """), {
            'user_id': user_id,
            'service': service.value,
        })
    row = result.fetchone()
    return row.latest_listened_at if row else None
