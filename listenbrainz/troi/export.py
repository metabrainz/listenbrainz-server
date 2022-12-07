import spotipy
from troi.core import generate_playlist
from troi.patches.playlist_from_listenbrainz import TransferPlaylistPatch


def export_to_spotify(lb_token, spotify_token, playlist_mbid, is_public):
    sp = spotipy.Spotify(auth=spotify_token)
    # TODO: store spotify user ids in external_service_oauth table
    spotify_user_id = sp.current_user()["id"]
    args = {
        "mbid": playlist_mbid,
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
    playlist = generate_playlist(TransferPlaylistPatch(), args)
    metadata = playlist.playlists[0].additional_metadata
    return metadata["external_urls"]["spotify"]
