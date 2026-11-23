from flask import current_app

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.apple import AppleService
from listenbrainz.domain.funkwhale import FunkwhaleService
from listenbrainz.domain.musicbrainz import get_musicbrainz_service_type
from listenbrainz.domain.navidrome import NavidromeService

# Each function below builds the props of one music service for an HTML page. data is the result of
# listenbrainz.db.global_props.get_global_props_data for the logged-in user, or None if nobody is logged in.


def get_current_spotify_user(data):
    """Returns the spotify access token and permissions for the current
    authenticated user. If the user is not authenticated or has not
    linked to a Spotify account, returns empty dict."""
    token = data and data["oauth_tokens"].get(ExternalServiceType.SPOTIFY.value)
    if not token:
        return {}
    return {
        "access_token": token["access_token"],
        "permission": token["scopes"]
    }


def get_current_youtube_user():
    """Returns the youtube access token for the current authenticated
    user and the youtube api key. If the user is not authenticated or
    has not linked to a Youtube account, returns empty dict."""
    return {
        "api_key": current_app.config["YOUTUBE_API_KEY"]
    }


def _access_token_only(data, service: ExternalServiceType):
    token = data and data["oauth_tokens"].get(service.value)
    if not token:
        return {}
    return {
        "access_token": token["access_token"],
    }


def get_current_critiquebrainz_user(data):
    """Returns the critiquebrainz access token for the current
    authenticated user. If the user is unauthenticated or has not
    linked their critiquebrainz account, returns empty dict."""
    return _access_token_only(data, ExternalServiceType.CRITIQUEBRAINZ)


def get_current_musicbrainz_user(data):
    """Returns the musicbrainz access token for the current
    authenticated user. If the user is unauthenticated or has not
    linked their musicbrainz account for submitting tags/ratings,
    returns empty dict."""
    return _access_token_only(data, get_musicbrainz_service_type())


def get_current_soundcloud_user(data):
    """Returns the soundcloud access token for the current
    authenticated user. If the user is unauthenticated or has not
    linked their soundcloud, returns empty dict."""
    return _access_token_only(data, ExternalServiceType.SOUNDCLOUD)


def get_current_apple_music_user(data):
    """Returns the apple music developer_token and the music_user_token for the
    current authenticated user. If the user is unauthenticated or has not
    linked their apple music account returns a dict with only the developer_token."""
    tokens = AppleService().fetch_access_token()
    developer_token = tokens["access_token"]
    token = data and data["oauth_tokens"].get(ExternalServiceType.APPLE.value)
    if not token:
        return {"developer_token": developer_token}
    return {
        "developer_token": developer_token,
        "music_user_token": token["refresh_token"]
    }


def get_current_funkwhale_user(data):
    """Returns the funkwhale access token and instance URL for the current user.
    If the user has not linked a Funkwhale account, returns empty dict.
    For Funkwhale, we return the first connected server if multiple exist.
    """
    connection = data and data["funkwhale"]
    if not connection:
        return {}

    user = FunkwhaleService().get_user_from_connection(data["user_id"], connection, refresh=True)
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


def get_current_navidrome_user(data):
    """Returns the navidrome access token and instance URL for the current user.
       If the user has not linked a Navidrome account, returns empty dict.
    """
    connection = data and data["navidrome"]
    if not connection:
        return {}
    return NavidromeService().get_auth_params(data["user_id"], connection) or {}
