from flask import current_app
from sqlalchemy import text
from troi.core import generate_playlist
from troi.internal.top_recordings_for_year import TopTracksYearPatch
from troi.internal.top_discoveries_for_year import TopDiscoveries
from troi.internal.top_missed_recordings_for_year import TopMissedTracksPatch
from troi.internal.top_new_recordings_you_listened_to_for_year import TopTracksYouListenedToPatch

from listenbrainz import db
from listenbrainz.db.year_in_music import insert_playlists


def get_all_users():
    # query = """SELECT musicbrainz_id, id as user_id FROM "user" """
    # with db.engine.connect() as conn:
    #     return conn.execute(text(query)).mappings().all()
    return [{"musicbrainz_id": "lucifer", "id": 5746}]


def get_all_patches():
    return [TopMissedTracksPatch(), TopTracksYearPatch(), TopDiscoveries(), TopTracksYouListenedToPatch()]


def yim_patch_runner(year):
    """ Run troi bot to generate playlists for all users """
    users = get_all_users()
    patches = get_all_patches()

    playlists = []
    for user in users:
        args = {
            "user_name": user["musicbrainz_id"],
            "token": current_app.config["WHITELISTED_AUTH_TOKENS"][0],
            "created_for": user["musicbrainz_id"],
            "upload": True
        }
        for patch in patches:
            try:
                playlist = generate_playlist(patch, args)
                if playlist is not None:
                    playlist_mbid = playlist.playlists[0].mbid
                    playlists.append((user["id"], f"playlist-{patch.slug()}", playlist_mbid))
            except Exception:
                current_app.logger.error("Error while generate YIM playlist:", exc_info=True)

    insert_playlists(year, playlists)
