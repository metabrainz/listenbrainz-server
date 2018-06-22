from listenbrainz import db
import sqlalchemy
from listenbrainz.db.exceptions import DatabaseException
from datetime import datetime
import pytz
from flask import current_app, url_for
import spotipy.oauth2


class Spotify:
    def __init__(self, user_id, user_token, token_expires, refresh_token,
                 last_updated, active, update_error):
        self.user_id = user_id
        self.user_token = user_token
        self.token_expires = token_expires
        self.refresh_token = refresh_token
        self.last_updated = last_updated
        self.active = active
        self.update_error = update_error

    @staticmethod
    def from_dbrow(row):
        return Spotify(row['user_id'], row['user_token'], row['token_expires'],
                       row['refresh_token'], row['last_updated'],
                       row['active'], row['update_error'])


def _get_spotify_oauth():
    client_id = current_app.config['SPOTIFY_CLIENT_ID']
    client_secret = current_app.config['SPOTIFY_CLIENT_SECRET']
    scope = 'user-read-recently-played'
    redirect_url = url_for(
            'profile.connect_spotify_callback',
            _external=True)
    return spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri=redirect_url, scope=scope)


def refresh_user_token(spotify_user):
    auth = _get_spotify_oauth()
    new_token = auth.refresh_access_token(spotify_user["refresh_token"])
    new_token = update_token(spotify_user["user_id"], new_token)
    return new_token


def _expires_at_to_datetime(timestamp):
    return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC)


def create_spotify(user_id, user_token, refresh_token, token_expires_ts):
    token_expires = _expires_at_to_datetime(token_expires_ts)
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO spotify (user_id, user_token, refresh_token, token_expires)
                         VALUES (:user_id, :user_token, :refresh_token, :token_expires)
        """), {
            "user_id": user_id,
            "user_token": user_token,
            "refresh_token": refresh_token,
            "token_expires": token_expires})


def delete_spotify(user_id):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM spotify
                  WHERE user_id = :user_id
        """), {
            "user_id": user_id
        })


def add_update_error(user_id, error_message):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE spotify
               SET last_updated = now()
                 , active = FALSE,
                 , update_error = :update_error
              WHERE user_id = :user_id
        """), {
            "user_id": user_id,
            "update_error": error_message
        })


def update_last_updated(user_id, success=True):
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
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id
                 , "user".musicbrainz_id
                 , user_token
                 , refresh_token
                 , last_updated
                 , token_expires
                 , token_expires < now() as token_expired
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
