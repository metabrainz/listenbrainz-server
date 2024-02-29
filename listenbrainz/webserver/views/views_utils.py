from flask import current_app
from flask_login import current_user
import spotipy
import requests

from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService
from listenbrainz.domain.soundcloud import SoundCloudService

PLAYLIST_TRACK_URI_PREFIX="https://musicbrainz.org/recording/"

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

def get_user_playlists(spotify_token):
    """ Get the user's playlists.
    """
    sp = spotipy.Spotify(auth=spotify_token)
    playlists = sp.current_user_playlists()
    return playlists

def get_tracks_from_playlist(spotify_token, playlist_id):
    """ Get the tracks from Spotify playlist.
    """
    sp = spotipy.Spotify(auth=spotify_token)
    playlists = sp.playlist_items(playlist_id, limit=100)
    return playlists

def mbid_mapping_spotify(track_name, artist_name):
    url = "https://api.listenbrainz.org/1/metadata/lookup/"
    params = {
        "artist_name": artist_name,
        "recording_name": track_name,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print("Error occurred:", response.status_code)
        
def listen_to_jspf(track):
    jspf_format = {
        "identifier": PLAYLIST_TRACK_URI_PREFIX + track["recording_mbid"],
        "title" : track["recording_name"],
        "creator": track["artist_credit_name"],
        "chosen": False,
        "selected":False
    }
    return jspf_format