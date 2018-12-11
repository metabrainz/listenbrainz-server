import pytz
from flask import current_app
import spotipy.oauth2

from listenbrainz.db import spotify as db_spotify
import datetime

SPOTIFY_API_RETRIES = 5


class Spotify:
    def __init__(self, user_id, musicbrainz_id, musicbrainz_row_id, user_token, token_expires,
                 refresh_token, last_updated, active, error_message, latest_listened_at):
        self.user_id = user_id
        self.user_token = user_token
        self.token_expires = token_expires
        self.refresh_token = refresh_token
        self.last_updated = last_updated
        self.active = active
        self.error_message = error_message
        self.musicbrainz_id = musicbrainz_id
        self.latest_listened_at = latest_listened_at
        self.musicbrainz_row_id = musicbrainz_row_id

    def get_spotipy_client(self):
        return spotipy.Spotify(auth=self.user_token)

    @property
    def last_updated_iso(self):
        if self.last_updated is None:
            return None
        return self.last_updated.isoformat() + "Z"

    @property
    def latest_listened_at_iso(self):
        if self.latest_listened_at is None:
            return None
        return self.latest_listened_at.isoformat() + "Z"

    @property
    def token_expired(self):
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=pytz.UTC)
        return now >= self.token_expires

    @staticmethod
    def from_dbrow(row):
        return Spotify(
           user_id=row['user_id'],
           user_token=row['user_token'],
           token_expires=row['token_expires'],
           refresh_token=row['refresh_token'],
           last_updated=row['last_updated'],
           active=row['active'],
           error_message=row['error_message'],
           musicbrainz_id=row['musicbrainz_id'],
           musicbrainz_row_id=row['musicbrainz_row_id'],
           latest_listened_at=row['latest_listened_at'],
        )

    def __str__(self):
        return "<Spotify(user:%s): %s>" % (self.user_id, self.musicbrainz_id)


def refresh_user_token(spotify_user):
    """ Refreshes the user token for the given spotify user.

    Args:
        spotify_user (domain.spotify.Spotify): the user whose token is to be refreshed

    Returns:
        user (domain.spotify.Spotify): the same user with updated tokens
    """
    auth = get_spotify_oauth()

    retries = SPOTIFY_API_RETRIES
    new_token = None
    while retries > 0:
        new_token = auth.refresh_access_token(spotify_user.refresh_token)
        if new_token:
            break
        retries -= 1
    if new_token is None:
        raise SpotifyAPIError('Could not refresh API Token for Spotify user')

    access_token = new_token['access_token']
    refresh_token = new_token['refresh_token']
    expires_at = new_token['expires_at']
    db_spotify.update_token(spotify_user.user_id, access_token, refresh_token, expires_at)
    return get_user(spotify_user.user_id)


def get_spotify_oauth():
    """ Returns a spotipy OAuth instance that can be used to authenticate with spotify.
    """
    client_id = current_app.config['SPOTIFY_CLIENT_ID']
    client_secret = current_app.config['SPOTIFY_CLIENT_SECRET']
    scope = 'user-read-recently-played'
    redirect_url = current_app.config['SPOTIFY_CALLBACK_URL']
    return spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri=redirect_url, scope=scope)


def get_user(user_id):
    """ Returns a Spotify instance corresponding to the specified LB row ID.
    If the user_id is not present in the spotify table, returns None

    Args:
        user_id (int): the ListenBrainz row ID of the user
    """
    row = db_spotify.get_user(user_id)
    if row:
        return Spotify.from_dbrow(row)
    return None


def remove_user(user_id):
    """ Delete user entry for user with specified ListenBrainz user ID.

    Args:
        user_id (int): the ListenBrainz row ID of the user
    """
    db_spotify.delete_spotify(user_id)


def add_new_user(user_id, spot_access_token):
    """Create a spotify row for a user based on OAuth access tokens

    Args:
        user_id: A flask auth `current_user.id`
        spot_access_token: A spotipy access token from SpotifyOAuth.get_access_token
    """

    access_token = spot_access_token['access_token']
    refresh_token = spot_access_token['refresh_token']
    expires_at = spot_access_token['expires_at']

    db_spotify.create_spotify(user_id, access_token, refresh_token, expires_at)


def get_active_users_to_process():
    """ Returns a list of Spotify user instances that need their Spotify listens imported.
    """
    return [Spotify.from_dbrow(row) for row in db_spotify.get_active_users_to_process()]


def update_last_updated(user_id, success=True, error_message=None):
    """ Update the last_update field for user with specified user ID.
    Also, set the user as active or inactive depending on whether their listens
    were imported without error.

    If there was an error, add the error to the db.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        success (bool): flag representing whether the last import was successful or not.
        error_message (str): the user-friendly error message to be displayed.
    """
    if error_message:
        db_spotify.add_update_error(user_id, error_message)
    else:
        db_spotify.update_last_updated(user_id, success)


def update_latest_listened_at(user_id, timestamp):
    """ Update the latest_listened_at field for user with specified ListenBrainz user ID.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        timestamp (int): the unix timestamp of the latest listen imported for the user
    """
    db_spotify.update_latest_listened_at(user_id, timestamp)


class SpotifyImporterException(Exception):
    pass

class SpotifyListenBrainzError(Exception):
    pass

class SpotifyAPIError(Exception):
    pass
