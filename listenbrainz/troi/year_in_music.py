from uuid import UUID

import ujson
from flask import current_app
from more_itertools import chunked
from psycopg2.extras import execute_values
from sqlalchemy import text
from troi.core import generate_playlist
from troi.patches.top_discoveries_for_year import TopDiscoveries
from troi.patches.top_missed_recordings_for_year import TopMissedTracksPatch
from troi.playlist import _serialize_to_jspf

from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.db.year_in_music import insert_playlists, insert_playlists_cover_art

USERS_PER_BATCH = 25


def get_all_users():
    query = """SELECT musicbrainz_id, id FROM "user" """
    with db.engine.connect() as conn:
        return conn.execute(text(query)).mappings().all()


def get_all_patches():
    return [TopMissedTracksPatch(), TopDiscoveries()]


def yim_patch_runner(year):
    """ Run troi bot to generate playlists for all users """
    users = get_all_users()
    patches = get_all_patches()
    batches = chunked(users, USERS_PER_BATCH)
    for batch in batches:
        playlists = generate_playlists_for_batch(batch, patches)
        insert_playlists(year, playlists)
        insert_playlists_cover_art(year, playlists)


def generate_playlists_for_batch(batch, patches):
    """ Generate playlists for a batch of users """
    yim_playlists = []
    for user in batch:
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
                    yim_playlists.append((user["id"], f"playlist-{patch.slug()}", data["playlist"]))
            except Exception:
                current_app.logger.error("Error while generate YIM playlist:", exc_info=True)

    return yim_playlists


def fixup_yim_playlists():
    """ Fix the year in YIM playlists"""
    query = """
            SELECT user_id
                 , data->'playlist-top-missed-recordings-for-year'->>'identifier' AS missed
                 , data->'playlist-top-discoveries-for-year'->>'identifier' AS discoveries
              FROM statistics.year_in_music
             WHERE year = 2022;
    """
    with db.engine.connect() as conn:
        rows = conn.execute(text(query)).mappings().all()

    playlist_mbids = []
    for row in rows:
        if row["missed"] is not None:
            playlist_mbids.append(row["missed"].split("/")[-2])

        if row["discoveries"] is not None:
            playlist_mbids.append(row["discoveries"].split("/")[-2])

    fix_query = """
          WITH t(mbid) AS (VALUES %s)
        UPDATE playlist.playlist p
           SET name = replace(name, '2023', '2022')
             , description = replace(description, '2023', '2022')
          FROM t
         WHERE t.mbid = p.mbid
    """
    with timescale.engine.begin() as conn, conn.connection.cursor() as cursor:
        execute_values(cursor, fix_query, [(UUID(mbid),) for mbid in playlist_mbids])
