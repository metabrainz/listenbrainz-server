from typing import List, Optional, Union

from data.model.external_service import ExternalServiceType
from listenbrainz import db, utils
import sqlalchemy


def save_token(user_id: int, service: ExternalServiceType, access_token: str, refresh_token: str,
               token_expires_ts: int, record_listens: bool, scopes: List[str], external_user_id: Optional[str] = None):
    """ Add a row to the external_service_oauth table for specified user with corresponding tokens and information.

    Args:
        user_id: the ListenBrainz row ID of the user
        service: the service for which the token can be used
        access_token: the access token used to access the user's listens
        refresh_token: the token used to refresh access tokens once they expire
        token_expires_ts: the unix timestamp at which the user_token will expire
        record_listens: True if user wishes to import listens, False otherwise
        scopes: the oauth scopes
        external_user_id: the user's id in the external linked service
    """
    # regardless of whether a row is inserted or updated, the end result of the query
    # should remain the same. if not so, weird things can happen as it is likely we
    # assume the defaults exist for new users while writing code elsewhere.
    # due to this reason, we update all columns in UPDATE section of following queries
    # to use the new values. any column which does not have a new value to be set should
    # be explicitly set to the default value (which would have been used if the row was
    # inserted instead).
    token_expires = utils.unix_timestamp_to_datetime(token_expires_ts)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO external_service_oauth
            (user_id, external_user_id, service, access_token, refresh_token, token_expires, scopes)
            VALUES
            (:user_id, :external_user_id, :service, :access_token, :refresh_token, :token_expires, :scopes)
            ON CONFLICT (user_id, service)
            DO UPDATE SET
                user_id = EXCLUDED.user_id,
                external_user_id = EXCLUDED.external_user_id,
                service = EXCLUDED.service,
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                token_expires = EXCLUDED.token_expires,
                scopes = EXCLUDED.scopes,
                last_updated = NOW()
            RETURNING id
            """), {
                "user_id": user_id,
                "external_user_id": external_user_id,
                "service": service.value,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires": token_expires,
                "scopes": scopes,
            })

        if record_listens:
            external_service_oauth_id = result.fetchone().id
            connection.execute(sqlalchemy.text("""
                INSERT INTO listens_importer
                (external_service_oauth_id, user_id, service)
                VALUES
                (:external_service_oauth_id, :user_id, :service)
                ON CONFLICT (user_id, service) DO UPDATE SET
                    external_service_oauth_id = EXCLUDED.external_service_oauth_id,
                    user_id = EXCLUDED.user_id,
                    service = EXCLUDED.service,
                    last_updated = NULL,
                    latest_listened_at = NULL,
                    error_message = NULL
                """), {
                "external_service_oauth_id": external_service_oauth_id,
                "user_id": user_id,
                "service": service.value
            })


def delete_token(user_id: int, service: ExternalServiceType, remove_import_log: bool):
    """ Delete a user from the external service table.

    Args:
        user_id: the ListenBrainz row ID of the user
        service: the service for which the token should be deleted
        remove_import_log: whether the (user, service) combination should be removed from the listens_importer table also
    """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM external_service_oauth
                  WHERE user_id = :user_id AND service = :service
        """), {
            "user_id": user_id,
            "service": service.value
        })
        if remove_import_log:
            connection.execute(sqlalchemy.text("""
                DELETE FROM listens_importer
                    WHERE user_id = :user_id AND service = :service
            """), {
                "user_id": user_id,
                "service": service.value
            })


def update_token(user_id: int, service: ExternalServiceType, access_token: str,
                 refresh_token: str, expires_at: int):
    """ Update the token for user with specified LB user ID and external service.

    Args:
        user_id: the ListenBrainz row ID of the user
        service: the service for which the token should be updated
        access_token: the new access token
        refresh_token: the new token used to refresh access tokens
        expires_at: the unix timestamp at which the access token expires
    """
    token_expires = utils.unix_timestamp_to_datetime(expires_at)
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE external_service_oauth
               SET access_token = :access_token
                 , refresh_token = :refresh_token
                 , token_expires = :token_expires
                 , last_updated = now()
             WHERE user_id = :user_id AND service = :service
        """), {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires": token_expires,
            "user_id": user_id,
            "service": service.value
        })


def get_token(user_id: int, service: ExternalServiceType) -> Union[dict, None]:
    """ Get details for user with specified user ID and service.

    Args:
        user_id: the ListenBrainz row ID of the user
        service: the service for which the token should be fetched
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id
                 , "user".musicbrainz_id
                 , "user".musicbrainz_row_id
                 , service
                 , access_token
                 , refresh_token
                 , last_updated
                 , token_expires
                 , scopes
                 , external_user_id
              FROM external_service_oauth
              JOIN "user"
                ON "user".id = external_service_oauth.user_id
             WHERE user_id = :user_id AND service = :service
            """), {
                'user_id': user_id,
                'service': service.value
            })
        return result.mappings().first()


def get_services(user_id: int) -> list[str]:
    """ Get the list of connected services for a given user

    Args:
        user_id: the ListenBrainz row ID of the user
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT service
              FROM external_service_oauth
             WHERE user_id = :user_id
            """), {'user_id': user_id})
        return [r.service for r in result.all()]
