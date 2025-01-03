import spotipy
from troi.patches.playlist_from_listenbrainz import TransferPlaylistPatch

def export_to_spotify(lb_token, spotify_token, is_public, playlist_mbid=None, jspf=None):
    sp = spotipy.Spotify(auth=spotify_token)
    # TODO: store spotify user ids in external_service_oauth table
    spotify_user_id = sp.current_user()["id"]
    args = {
        "mbid": playlist_mbid,
        "jspf": jspf,
        "read_only_token": lb_token,
        "spotify": {
            "user_id": spotify_user_id,
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
    if not metadata:
        raise Exception("Failed to export playlist to Apple Music")
    return metadata["external_urls"]["apple_music"]
