from listenbrainz import db
import sqlalchemy
from listenbrainz.db.exceptions import DatabaseException
from datetime import datetime
import pytz
from flask import current_app, url_for
import spotipy.oauth2


def _expires_at_to_datetime(timestamp):
    """ Converts expires_at timestamp received from Spotify to a datetime object

    Args:
        timestamp (int): the unix timestamp to be converted to datetime

    Returns:
        A datetime object with timezone UTC corresponding to the provided timestamp
    """
    return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC)


def create_spotify(user_id, user_token, refresh_token, token_expires_ts):
    """ Add a row to the spotify table for specified user with corresponding
    Spotify tokens and information.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        user_token (str): the Spotify access token used to access the user's Spotify listens.
        refresh_token (str): the token used to refresh Spotify access tokens once they expire
        token_expires_ts (int): the unix timestamp at which the user_token will expire
    """
    token_expires = _expires_at_to_datetime(token_expires_ts)
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO spotify (user_id, user_token, refresh_token, token_expires)
                 VALUES (:user_id, :user_token, :refresh_token, :token_expires)
            """), {
                "user_id": user_id,
                "user_token": user_token,
                "refresh_token": refresh_token,
                "token_expires": token_expires,
            })


def delete_spotify(user_id):
    """ Delete a user from the spotify table.

    Args:
        user_id (int): the ListenBrainz row ID of the user
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM spotify
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
            UPDATE spotify
               SET last_updated = now()
                 , active = 'f'
                 , update_error = :update_error
              WHERE user_id = :user_id
        """), {
            "user_id": user_id,
            "update_error": error_message
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
            UPDATE spotify
               SET last_updated = now()
                 , active = :active
              WHERE user_id = :user_id
        """), {
            "user_id": user_id,
            "active": success
        })


def update_token(user_id, token):
    """ Update token for user with specified LB user ID.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        token (dict): a dict containing the following keys
                      {
                        'access_token': the new access token,
                        'refresh_token': the new token used to refresh access tokens,
                        'expires_at': the unix timestamp at which the access token expires
                      }
    Returns:
        the new token
    """
    token_expires = _expires_at_to_datetime(token["expires_at"])
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE spotify
               SET user_token = :user_token
                 , refresh_token = :refresh_token
                 , token_expires = :token_expires
             WHERE user_id = :user_id
        """), {
            "user_token": token["access_token"],
            "refresh_token": token["refresh_token"],
            "token_expires": token_expires,
            "user_id": user_id
        })
        token["user_id"] = user_id
    return token


def get_active_users_to_process():
    """ Returns a list of users whose listens should be imported from Spotify.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id
                 , "user".musicbrainz_id
                 , user_token
                 , refresh_token
                 , last_updated
                 , token_expires
                 , token_expires < now() as token_expired
                 , active
                 , update_error
              FROM spotify
              JOIN "user"
                ON "user".id = spotify.user_id
             WHERE spotify.active = 't'
          ORDER BY last_updated ASC
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
              FROM spotify
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
                 , user_token
                 , refresh_token
                 , last_updated
                 , token_expires
                 , token_expires < now() as token_expired
                 , active
                 , update_error
              FROM spotify
              JOIN "user"
                ON "user".id = spotify.user_id
             WHERE user_id = :user_id
            """), {
                'user_id': user_id,
            })
        if result.rowcount > 0:
            return dict(result.fetchone())
        return None
