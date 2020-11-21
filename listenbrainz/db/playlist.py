from listenbrainz.db.model import playlist as model_playlist


def get_by_id(playlist_id: str) -> model_playlist.Playlist:
    pass


def insert(playlist: model_playlist.WritablePlaylist) -> model_playlist.Playlist:
    pass


def update(playlist: model_playlist.Playlist) -> model_playlist.Playlist:
    pass


