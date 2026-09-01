from troi.service import Service

import listenbrainz.db.user as db_user
import listenbrainz.db.playlist as db_playlist
from listenbrainz.webserver import db_conn, ts_conn


class LBRadioPlaylistService(Service):
    """Replaces the GET https://api.listenbrainz.org/1/playlist/{mbid} HTTP call
    in LBRadioPlaylistRecordingElement with a direct DB lookup."""

    SLUG = "playlist"

    def __init__(self):
        super().__init__(self.SLUG)

    def fetch(self, playlist_mbid: str, auth_token: str | None) -> list[str]:
        playlist = db_playlist.get_by_mbid(db_conn, ts_conn, playlist_mbid, load_recordings=True)
        if playlist is None:
            raise RuntimeError(f"Cannot find playlist {playlist_mbid}.")

        user_id = None
        if auth_token is not None:
            user = db_user.get_by_token(db_conn, auth_token)
            if user is not None:
                user_id = user["id"]

        if not playlist.is_visible_by(user_id):
            raise RuntimeError(f"Cannot find playlist {playlist_mbid}.")

        return [str(r.mbid) for r in playlist.recordings]
