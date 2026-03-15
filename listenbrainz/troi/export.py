import spotipy
from troi.patches.playlist_from_listenbrainz import TransferPlaylistPatch
from listenbrainz.metadata_cache.soundcloud.client import SoundCloud

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
    if not playlist.playlists:
        raise Exception(
            "Apple Music export returned no playlists. The playlist may be empty or all tracks failed to match."
        )
    metadata = playlist.playlists[0].additional_metadata
    if not metadata or "external_urls" not in metadata or "apple_music" not in metadata["external_urls"]:
        raise Exception(
            "Apple Music export did not return a playlist URL. Check that your Apple Music account is properly linked."
        )
    return metadata["external_urls"]["apple_music"]


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
