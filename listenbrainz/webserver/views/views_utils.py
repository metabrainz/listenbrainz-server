from listenbrainz.domain.spotify import SpotifyService
from flask_login import current_user


def get_current_spotify_user():
    """Returns the spotify access token and permissions for the current
    authenticated user. If the user is not authenticated or has not linked
    to a Spotify account, returns empty dict."""
    if not current_user.is_authenticated:
        return {}
    user = SpotifyService().get_user(current_user.id)
    if user is None:
        return {}
    return {
        "access_token": user["access_token"],
        "permission": user["scopes"]
    }
