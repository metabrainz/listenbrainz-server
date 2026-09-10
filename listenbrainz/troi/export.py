import spotipy
from troi.patches.playlist_from_listenbrainz import TransferPlaylistPatch
from listenbrainz.metadata_cache.soundcloud.client import SoundCloud


class PlaylistExportError(Exception):
    """Raised when an external service cannot provide an exported playlist URL."""


def export_to_spotify(lb_token, spotify_token, is_public, playlist_mbid=None, jspf=None):
    args = {
        "mbid": playlist_mbid,
        "jspf": jspf,
        "read_only_token": lb_token,
        "spotify": {
            "token": spotify_token,
            "is_public": is_public,
            "is_collaborative": False
        },
        "upload": True,
        "echo": False,
        "min_recordings": 1
    }
    patch = TransferPlaylistPatch(args)
    playlist = patch.generate_playlist()
    metadata = playlist.playlists[0].additional_metadata
    return metadata["external_urls"]["spotify"]


def export_to_apple_music(lb_token, apple_music_token, music_user_token, is_public, playlist_mbid=None, jspf=None):
    args = {
        "mbid": playlist_mbid,
        "jspf": jspf,
        "read_only_token": lb_token,
        "apple_music": {
            "developer_token": apple_music_token,
            "music_user_token": music_user_token,
            "is_public": is_public
        },
        "upload": True,
        "echo": False,
        "min_recordings": 1
    }
    patch = TransferPlaylistPatch(args)
    playlist = patch.generate_playlist()
    metadata = playlist.playlists[0].additional_metadata
    if not isinstance(metadata, dict):
        raise PlaylistExportError("Apple Music did not return playlist metadata.")

    url = metadata.get("external_urls", {}).get("apple_music")
    if not url:
        raise PlaylistExportError("Apple Music did not return an exported playlist URL.")
    return url


def export_to_soundcloud(lb_token, soundcloud_token, is_public, playlist_mbid=None, jspf=None):
    args = {
        "mbid": playlist_mbid,
        "jspf": jspf,
        "read_only_token": lb_token,
        "soundcloud": {
            "token": soundcloud_token,
            "is_public": is_public,
        },
        "upload": True,
        "echo": False,
        "min_recordings": 1
    }
    patch = TransferPlaylistPatch(args)
    playlist = patch.generate_playlist()
    metadata = playlist.playlists[0].additional_metadata
    return metadata["external_urls"]["soundcloud"]
