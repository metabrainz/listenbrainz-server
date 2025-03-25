from datetime import datetime, timezone
from typing import Optional, Union

from sqlalchemy import text

from data.model.external_service import ExternalServiceType
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
            'timestamp': datetime.fromtimestamp(timestamp, timezone.utc),
        })
    db_conn.commit()


def get_latest_listened_at(db_conn, user_id: int, service: ExternalServiceType) -> Optional[datetime]:
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


def get_active_users_to_process(db_conn, service, exclude_error=False) -> list[dict]:
    """ Returns a list of users whose listens should be imported from the external service.
    """
    filters = ["external_service_oauth.service = :service"]
    if exclude_error:
        filters.append("error_message IS NULL")
    filter_str = " AND ".join(filters)

    result = db_conn.execute(text(f"""
        SELECT external_service_oauth.user_id
             , "user".musicbrainz_id
             , "user".musicbrainz_row_id
             , access_token
             , refresh_token
             , listens_importer.last_updated
             , token_expires
             , scopes
             , latest_listened_at
             , external_service_oauth.external_user_id
             , error_message
             , is_paused
          FROM external_service_oauth
          JOIN "user"
            ON "user".id = external_service_oauth.user_id
          JOIN listens_importer
            ON listens_importer.external_service_oauth_id = external_service_oauth.id
         WHERE {filter_str}
      ORDER BY latest_listened_at DESC NULLS LAST
    """), {"service": service.value})
    users = [row for row in result.mappings()]
    db_conn.rollback()
    return users
