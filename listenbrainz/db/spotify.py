from listenbrainz import db, utils
import sqlalchemy
from listenbrainz.db.exceptions import DatabaseException
from datetime import datetime
import pytz
from flask import current_app, url_for
import spotipy.oauth2


def create_spotify(user_id, user_token, refresh_token, token_expires_ts, record_listens, permission):
    """ Add a row to the spotify table for specified user with corresponding
    Spotify tokens and information.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        user_token (str): the Spotify access token used to access the user's Spotify listens.
        refresh_token (str): the token used to refresh Spotify access tokens once they expire
        token_expires_ts (int): the unix timestamp at which the user_token will expire
        record_listens (bool): True if user wishes to import listens from Spotify, False otherwise
        permission (str): the scope of the permissions granted to us by the user as a space seperated string
    """
    token_expires = utils.unix_timestamp_to_datetime(token_expires_ts)
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO spotify_auth (user_id, user_token, refresh_token, token_expires, record_listens, permission)
                 VALUES (:user_id, :user_token, :refresh_token, :token_expires, :record_listens, :permission)
            """), {
                "user_id": user_id,
                "user_token": user_token,
                "refresh_token": refresh_token,
                "token_expires": token_expires,
                "record_listens": record_listens,
                "permission": permission,
            })


def delete_spotify(user_id):
    """ Delete a user from the spotify table.

    Args:
        user_id (int): the ListenBrainz row ID of the user
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM spotify_auth
                  WHERE user_id = :user_id
        """), {
            "user_id": user_id
        })


def add_update_error(user_id, error_message):
    """ Add an error message to be shown to the user and set the user as inactive.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        error_message (str): the user-friendly error message to be displayed
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE spotify_auth
               SET last_updated = now()
                 , record_listens = 'f'
                 , error_message = :error_message
              WHERE user_id = :user_id
        """), {
            "user_id": user_id,
            "error_message": error_message
        })


def update_last_updated(user_id, success=True):
    """ Update the last_updated field for the user with specified LB user_id.
    Also, set the user as active or inactive depending on whether their listens
    were imported correctly.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        success (bool): flag representing whether the user's import was successful or not
                        if False, this function marks the user as inactive.
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE spotify_auth
               SET last_updated = now()
                 , record_listens = :record_listens
              WHERE user_id = :user_id
        """), {
            "user_id": user_id,
            "record_listens": success,
        })


def update_latest_listened_at(user_id, timestamp):
    """ Update the timestamp of the last listen imported for the user with
    specified LB user ID.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        timestamp (int): the unix timestamp of the latest listen imported for the user
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE spotify_auth
               SET latest_listened_at = :timestamp
             WHERE user_id = :user_id
            """), {
                'user_id': user_id,
                'timestamp': utils.unix_timestamp_to_datetime(timestamp),
            })


def update_token(user_id, access_token, refresh_token, expires_at):
    """ Update token for user with specified LB user ID.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        access_token (str): the new access token,
        refresh_token (str): the new token used to refresh access tokens,
        expires_at (int): the unix timestamp at which the access token expires

    Returns:
        the new token in dict form
    """
    token_expires = utils.unix_timestamp_to_datetime(expires_at)
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE spotify_auth
               SET user_token = :user_token
                 , refresh_token = :refresh_token
                 , token_expires = :token_expires
             WHERE user_id = :user_id
        """), {
            "user_token": access_token,
            "refresh_token": refresh_token,
            "token_expires": token_expires,
            "user_id": user_id,
        })


def get_active_users_to_process():
    """ Returns a list of users whose listens should be imported from Spotify.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id
                 , "user".musicbrainz_id
                 , "user".musicbrainz_row_id
                 , user_token
                 , refresh_token
                 , last_updated
                 , latest_listened_at
                 , token_expires
                 , token_expires < now() as token_expired
                 , record_listens
                 , error_message
                 , permission
              FROM spotify_auth
              JOIN "user"
                ON "user".id = spotify_auth.user_id
             WHERE spotify_auth.record_listens = 't'
          ORDER BY latest_listened_at DESC NULLS LAST
        """))
        return [dict(row) for row in result.fetchall()]


def get_token_for_user(user_id):
    """Gets token for user with specified User ID if user has already authenticated.

    Args:
        user_id (int): the ListenBrainz row ID of the user

    Returns:
        token: the user token if it exists, None otherwise
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_token
              FROM spotify_auth
             WHERE user_id = :user_id
            """), {
                'user_id': user_id,
            })

        if result.rowcount > 0:
            return result.fetchone()['user_token']
        return None


def get_user(user_id):
    """ Get spotify details for user with specified user ID.

    Args:
        user_id (int): the ListenBrainz row ID of the user
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id
                 , "user".musicbrainz_id
                 , "user".musicbrainz_row_id
                 , user_token
                 , refresh_token
                 , last_updated
                 , latest_listened_at
                 , token_expires
                 , token_expires < now() as token_expired
                 , record_listens
                 , error_message
                 , permission
              FROM spotify_auth
              JOIN "user"
                ON "user".id = spotify_auth.user_id
             WHERE user_id = :user_id
            """), {
                'user_id': user_id,
            })
        if result.rowcount > 0:
            return dict(result.fetchone())
        return None
