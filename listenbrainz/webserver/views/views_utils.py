from flask import current_app
from flask_login import current_user

from listenbrainz.domain.apple import AppleService
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService
from listenbrainz.domain.soundcloud import SoundCloudService
from listenbrainz.domain.funkwhale import FunkwhaleService
from listenbrainz.db import funkwhale as db_funkwhale


def get_current_spotify_user():
    """Returns the spotify access token and permissions for the current
    authenticated user. If the user is not authenticated or has not
    linked to a Spotify account, returns empty dict."""
    if not current_user.is_authenticated:
        return {}
    user = SpotifyService().get_user(current_user.id)
    if user is None:
        return {}
    return {
        "access_token": user["access_token"],
        "permission": user["scopes"]
    }


def get_current_youtube_user():
    """Returns the youtube access token for the current authenticated
    user and the youtube api key. If the user is not authenticated or
    has not linked to a Youtube account, returns empty dict."""
    return {
        "api_key": current_app.config["YOUTUBE_API_KEY"]
    }


def get_current_critiquebrainz_user():
    """Returns the critiquebrainz access token for the current
    authenticated user. If the user is unauthenticated or has not
    linked their critiquebrainz account, returns empty dict."""
    if not current_user.is_authenticated:
        return {}
    user = CritiqueBrainzService().get_user(current_user.id)
    if user is None:
        return {}
    return {
        "access_token": user["access_token"],
    }


def get_current_musicbrainz_user():
    """Returns the musicbrainz access token for the current
    authenticated user. If the user is unauthenticated or has not
    linked their musicbrainz account for submitting tags/ratings,
    returns empty dict."""
    if not current_user.is_authenticated:
        return {}
    user = MusicBrainzService().get_user(current_user.id)
    if user is None:
        return {}
    return {
        "access_token": user["access_token"],
    }


def get_current_soundcloud_user():
    """Returns the soundcloud access token for the current
    authenticated user. If the user is unauthenticated or has not
    linked their soundcloud, returns empty dict."""
    if not current_user.is_authenticated:
        return {}
    user = SoundCloudService().get_user(current_user.id)
    if user is None:
        return {}
    return {
        "access_token": user["access_token"],
    }


def get_current_apple_music_user():
    """Returns the apple music developer_token and the music_user_token for the
    current authenticated user. If the user is unauthenticated or has not
    linked their apple music account returns a dict with only the developer_token."""
    tokens = AppleService().fetch_access_token()
    developer_token = tokens["access_token"]
    if not current_user.is_authenticated:
        return {"developer_token": developer_token}
    user = AppleService().get_user(current_user.id)
    if user is None:
        return {"developer_token": developer_token}
    return {
        "developer_token": developer_token,
        "music_user_token": user["refresh_token"]
    }


def get_current_funkwhale_user():
    """Returns the funkwhale access token and instance URL for the current user.
    If the user has not linked a Funkwhale account, returns empty dict.
    For Funkwhale, we return the first connected server if multiple exist."""
    # Get all tokens for this user, join with servers
    from sqlalchemy import text
    from listenbrainz.webserver import db_conn
    result = db_conn.execute(text('''
        SELECT t.*, s.host_url, s.client_id, s.client_secret, s.scopes
        FROM funkwhale_tokens t
        JOIN funkwhale_servers s ON t.funkwhale_server_id = s.id
        WHERE t.user_id = :user_id
        ORDER BY t.id ASC
        LIMIT 1
    '''), {'user_id': current_user.id})
    row = result.mappings().first()
    if not row:
        return {}
    return {
        'access_token': row['access_token'],
        'instance_url': row['host_url'],
        'client_id': row['client_id'],
        'client_secret': row['client_secret'],
        'scopes': row['scopes'],
        'token_expiry': row['token_expiry'],
        'refresh_token': row['refresh_token'],
        'funkwhale_server_id': row['funkwhale_server_id']
    }
