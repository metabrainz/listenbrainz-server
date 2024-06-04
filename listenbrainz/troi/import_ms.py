from troi.patches.playlist_from_ms import ImportPlaylistPatch

def import_from_spotify(token, user, playlist_id):
    args = {
        "ms_token": token,
        "token": user,
        "playlist_id": playlist_id,
        "upload": True,
        "created_for": None,
        "echo": False,
        "min_recordings": 1
    }
    patch = ImportPlaylistPatch(args)
    playlist = patch.generate_playlist()
    result = playlist.get_jspf()
    result.update({'identifier': playlist.playlists[0].mbid})

    return result
