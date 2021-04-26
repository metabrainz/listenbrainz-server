from listenbrainz.domain.spotify import SpotifyService
from flask_login import current_user


def get_current_spotify_user():
    if not current_user.is_authenticated:
        return {}
    user = SpotifyService().get_user(current_user.id)
    if user is None:
        return {}
    return {
        "access_token": user["access_token"],
        "permission": user["scopes"]
    }
