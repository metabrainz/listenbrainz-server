import spotipy
from troi.core import generate_playlist


def export_to_spotify(lb_token, spotify_token, playlist_mbid, is_public):
    sp = spotipy.Spotify(auth=spotify_token)
    # TODO: store spotify user ids in external_service_oauth table
    spotify_user_id = sp.current_user()["id"]
    spotify_args = {
        "user_id": spotify_user_id,
        "token": spotify_token,
        "is_public": is_public,
        "is_collaborative": False
    }
    playlist = generate_playlist("resave-playlist", args=[playlist_mbid, lb_token], spotify=spotify_args, upload=True)
    return playlist.playlists[0].external_urls[0]
