from flask import current_app
from flask_login import current_user

from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService
from listenbrainz.domain.soundcloud import SoundCloudService


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
