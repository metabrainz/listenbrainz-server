from flask import current_app
from flask_login import current_user

from listenbrainz.domain.apple import AppleService
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService
from listenbrainz.domain.soundcloud import SoundCloudService
from listenbrainz.domain.funkwhale import FunkwhaleService
from listenbrainz.db import funkwhale as db_funkwhale
from listenbrainz.webserver import db_conn


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
    For Funkwhale, we return the first connected server if multiple exist.
    """
    if not current_user.is_authenticated:
        return {}

    # Get all tokens for this user to find the first server
    # Use the first server (consistent with frontend logic)
    tokens = db_funkwhale.get_all_user_tokens(db_conn, current_user.id)
    if not tokens:
        return {}

    first_token = tokens[0]
    service = FunkwhaleService()
    user = service.get_user(current_user.id, first_token["host_url"], refresh=True)
    if not user:
        return {}

    return {
        "access_token": user["access_token"],
        "instance_url": user["host_url"],
        "client_id": user["client_id"],
        "client_secret": user["client_secret"],
        "token_expiry": user["token_expiry"],
        "refresh_token": user["refresh_token"],
        "funkwhale_server_id": user["funkwhale_server_id"]
    }


def get_current_navidrome_user():
    """Returns the navidrome access token and instance URL for the current user.
    If the user has not linked a Navidrome account, returns empty dict."""
    if not current_user.is_authenticated:
        return {}
    
    import listenbrainz.db.navidrome as db_navidrome
    from listenbrainz.domain.navidrome import NavidromeService
    
    connection = db_navidrome.get_user_token(db_conn, current_user.id)
    if not connection:
        return {}
    
    # Get fresh auth parameters for this user
    navidrome_service = NavidromeService()
    auth_params = navidrome_service.get_auth_params_for_user(current_user.id)
    
    if not auth_params:
        return {}
    
    return {
        'encrypted_password': auth_params['token'],  # Fresh MD5 hash
        'salt': auth_params['salt'],                 # Fresh random salt  
        'instance_url': connection['host_url'],
        'username': connection['username'],
        'user_id': str(current_user.id)
    }
