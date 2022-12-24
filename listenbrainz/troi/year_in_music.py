import ujson
from flask import current_app
from troi.core import generate_playlist
from troi.patches.top_discoveries_for_year import TopDiscoveries
from troi.patches.top_missed_recordings_for_year import TopMissedTracksPatch
from troi.playlist import _serialize_to_jspf

from listenbrainz.db.year_in_music import insert_playlists


def get_all_users():
    # query = """SELECT musicbrainz_id, id FROM "user" """
    # with db.engine.connect() as conn:
    #     return conn.execute(text(query)).mappings().all()
    return [{"musicbrainz_id": "lucifer", "id": 5746}]


def get_all_patches():
    return [TopMissedTracksPatch(), TopDiscoveries()]


def yim_patch_runner(year):
    """ Run troi bot to generate playlists for all users """
    users = get_all_users()
    patches = get_all_patches()

    yim_playlists = []
    for user in users:
        args = {
            "user_name": user["musicbrainz_id"],
            "user_id": user["id"],
            "token": current_app.config["WHITELISTED_AUTH_TOKENS"][0],
            "created_for": user["musicbrainz_id"],
            "mb_db_connect_str": current_app.config["SQLALCHEMY_DATABASE_URI"],
            "lb_db_connect_str": current_app.config["SQLALCHEMY_TIMESCALE_URI"],
            "upload": True
        }
        for patch in patches:
            try:
                playlist_element = generate_playlist(patch, args)
                if playlist_element is not None:
                    playlist = playlist_element.playlists[0]
                    data = _serialize_to_jspf(playlist)
                    data["playlist"]["identifier"] = "https://listenbrainz.org/playlist/" + playlist.mbid + "/"
                    yim_playlists.append((
                        user["id"],
                        f"playlist-{patch.slug()}",
                        ujson.dumps(data["playlist"]),
                    ))
            except Exception:
                current_app.logger.error("Error while generate YIM playlist:", exc_info=True)

    insert_playlists(year, yim_playlists)
