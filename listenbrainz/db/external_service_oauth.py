from typing import List, Union

from data.model.external_service import ExternalServiceType
from listenbrainz import db, utils
import sqlalchemy


def save_token(user_id: int, service: ExternalServiceType, access_token: str, refresh_token: str,
               token_expires_ts: int, record_listens: bool, scopes: List[str]):
    """ Add a row to the external_service_oauth table for specified user with corresponding tokens and information.

    Args:
        user_id: the ListenBrainz row ID of the user
        service: the service for which the token can be used
        access_token: the access token used to access the user's listens
        refresh_token: the token used to refresh access tokens once they expire
        token_expires_ts: the unix timestamp at which the user_token will expire
        record_listens: True if user wishes to import listens, False otherwise
        scopes: the oauth scopes
    """
    token_expires = utils.unix_timestamp_to_datetime(token_expires_ts)
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO external_service_oauth 
            (user_id, service, access_token, refresh_token, token_expires, scopes)
            VALUES 
            (:user_id, :service, :access_token, :refresh_token, :token_expires, :scopes)
            RETURNING id
            """), {
                "user_id": user_id,
                "service": service.value,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires": token_expires,
                "scopes": scopes,
            })

        if record_listens:
            external_service_oauth_id = result.fetchone()['id']
            connection.execute(sqlalchemy.text("""
                INSERT INTO listens_importer
                (external_service_oauth_id, user_id, service)
                VALUES
                (:external_service_oauth_id, :user_id, :service)
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
    with db.engine.connect() as connection:
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
    with db.engine.connect() as connection:
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
              FROM external_service_oauth
              JOIN "user"
                ON "user".id = external_service_oauth.user_id
             WHERE user_id = :user_id AND service = :service
            """), {
                'user_id': user_id,
                'service': service.value
            })
        if result.rowcount > 0:
            return dict(result.fetchone())
        return None
