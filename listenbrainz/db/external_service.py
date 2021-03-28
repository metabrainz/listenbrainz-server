import json

from listenbrainz import db, utils
import sqlalchemy


def save_token(user_id, service, access_token, refresh_token, token_expires_ts, record_listens, service_details):
    """ Add a row to the external_auth table for specified user with corresponding tokens and information.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.external_service.ExternalService): the service for which the token can be used for
        access_token (str): the access token used to access the user's listens
        refresh_token (str): the token used to refresh access tokens once they expire
        token_expires_ts (int): the unix timestamp at which the user_token will expire
        record_listens (bool): True if user wishes to import listens, False otherwise
        service_details (dict): service specific details
    """
    token_expires = utils.unix_timestamp_to_datetime(token_expires_ts)
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO external_auth 
            (user_id, service, access_token, refresh_token, token_expires, record_listens, service_details)
            VALUES 
            (:user_id, :service, :access_token, :refresh_token, :token_expires, :record_listens, :service_details)
            """), {
                "user_id": user_id,
                "service": service.value,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires": token_expires,
                "record_listens": record_listens,
                "service_details": json.dumps(service_details),
            })


def delete_token(user_id, service):
    """ Delete a user from the external service table.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.external_service.ExternalService): the service for which the token should be deleted
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM external_auth
                  WHERE user_id = :user_id AND service = :service
        """), {
            "user_id": user_id,
            "service": service.value
        })


def update_token(user_id, service, access_token, refresh_token, expires_at):
    """ Update the token for user with specified LB user ID and external service.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.external_service.ExternalService): the service for which the token should be updated
        access_token (str): the new access token
        refresh_token (str): the new token used to refresh access tokens
        expires_at (int): the unix timestamp at which the access token expires
    """
    token_expires = utils.unix_timestamp_to_datetime(expires_at)
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE external_auth
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


def get_token(user_id, service):
    """ Get details for user with specified user ID and service.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.external_service.ExternalService): the service for which the token should be fetched
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id
                 , "user".musicbrainz_id
                 , "user".musicbrainz_row_id
                 , service
                 , access_token
                 , refresh_token
                 , token_expires
                 , token_expires < now() as token_expired
                 , record_listens
                 , service_details
              FROM external_auth
              JOIN "user"
                ON "user".id = external_auth.user_id
             WHERE user_id = :user_id AND service = :service
            """), {
                'user_id': user_id,
                'service': service.value
            })
        if result.rowcount > 0:
            return dict(result.fetchone())
        return None

