import pytz
from flask import current_app, url_for
import spotipy.oauth2

from listenbrainz.db import spotify as db_spotify
import datetime


class Spotify:
    def __init__(self, user_id, musicbrainz_id, user_token, token_expires, refresh_token,
                 last_updated, active, update_error_message):
        self.user_id = user_id
        self.user_token = user_token
        self.token_expires = token_expires
        self.refresh_token = refresh_token
        self.last_updated = last_updated
        self.active = active
        self.update_error_message = update_error_message
        self.musicbrainz_id = musicbrainz_id

    def get_spotipy_client(self):
        return spotipy.Spotify(auth=self.user_token)

    def nice_last_updated(self):
        if not self.last_updated:
            return 'never'
        return self.last_updated

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
           update_error_message=row['update_error'],
           musicbrainz_id=row['musicbrainz_id'],
        )

    def __str__(self):
        return "<Spotify(user:%s)>" % self.user_id

# TODO: All documentation for these
# TODO: Tests

def refresh_user_token(spotify_user):
    auth = get_spotify_oauth()
    new_token = auth.refresh_access_token(spotify_user.refresh_token)
    access_token = new_token['access_token']
    refresh_token = new_token['refresh_token']
    expires_at = new_token['expires_at']
    db_spotify.update_token(spotify_user.user_id, access_token, refresh_token, expires_at)


def get_spotify_oauth():
    client_id = current_app.config['SPOTIFY_CLIENT_ID']
    client_secret = current_app.config['SPOTIFY_CLIENT_SECRET']
    scope = 'user-read-recently-played'
    redirect_url = url_for(
            'profile.connect_spotify_callback',
            _external=True)
    return spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri=redirect_url, scope=scope)


def get_user(user_id):
    row = db_spotify.get_user(user_id)
    if row:
        return Spotify.from_dbrow(row)


def delete_spotify(user_id):
    db_spotify.delete_spotify(user_id)


def create_spotify(user_id, spot_access_token):
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
    return [Spotify.from_dbrow(row) for row in db_spotify.get_active_users_to_process()]


def update_last_updated(user_id, success=True, error_message=None):
    db_spotify.update_last_updated(user_id, success, error_message)
