""" Common code for processing troi playlists generated in spark """

import json

from flask import current_app
from psycopg2.extras import execute_values, DictCursor
from psycopg2.sql import SQL, Literal
from spotipy import Spotify
from sqlalchemy import text
from troi import Recording, Playlist
from troi.tools.spotify_lookup import submit_to_spotify

from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.db.playlist import LISTENBRAINZ_USER_ID
from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.troi.utils import get_existing_playlist_urls, SPOTIFY_EXPORT_PREFERENCE


def get_user_details(slug, user_ids):
    """ For all users, get usernames, export preferences and existing spotify playlist urls if preferred to export """
    users_for_urls = []
    details = {}

    query = """
          WITH spotify_exports AS (
                SELECT u.id as user_id
                     , true AS export
                  FROM "user" u
                  JOIN user_setting us
                    ON us.user_id = u.id
                  JOIN external_service_oauth eso
                    ON u.id = eso.user_id
                 WHERE u.id = ANY(:user_ids)
                   AND eso.service = 'spotify'
                   AND eso.scopes @> ARRAY['playlist-modify-public']
                   AND (us.troi->:export_preference)::bool
             )
                SELECT u.id as user_id
                     , u.musicbrainz_id AS musicbrainz_id
                     , coalesce(se.export, false) AS export_to_spotify
                  FROM "user" u
             LEFT JOIN spotify_exports se
                    ON u.id = se.user_id
                 WHERE u.id = ANY(:user_ids)
    """
    with db.engine.connect() as conn:
        results = conn.execute(text(query), {"user_ids": user_ids, "export_preference": SPOTIFY_EXPORT_PREFERENCE})
        for r in results:
            details[r.user_id] = {"username": r.musicbrainz_id, "export_to_spotify": r.export_to_spotify}

            if r.export_to_spotify:
                users_for_urls.append(r.user_id)
    with timescale.engine.connect() as ts_conn:
        existing_urls = get_existing_playlist_urls(ts_conn, users_for_urls, slug)
    for user_id, detail in details.items():
        detail["existing_url"] = existing_urls.get(user_id)

    return details


def export_to_spotify(playlists):
    """ Export the playlists to spotify.

        If a playlist url for the given user and slug already exists, its updated otherwise a new one is created.
    """
    service = SpotifyService()
    for playlist in playlists:
        try:
            user_id = playlist["user_id"]
            user = service.get_user(user_id, refresh=True)
            if user is None:
                current_app.logger.error("Unable to fetch spotify details for user_id: %d", user_id)
                continue

            sp = Spotify(auth=user["access_token"])

            recordings = [Recording(mbid=mbid) for mbid in playlist["recordings"]]
            playlist_element = Playlist(
                name=playlist["name"],
                description=playlist["description"],
                recordings=recordings
            )
            playlist_url, _ = submit_to_spotify(
                sp,
                playlist_element,
                user["external_user_id"],
                existing_url=playlist["existing_url"]
            )
            playlist["additional_metadata"].update({"external_urls": {"spotify": playlist_url}})
        except Exception:
            current_app.logger.error("Unable to export playlist to spotify:", exc_info=True)


def insert_recordings(cursor, playlist_id: str, recordings: list):
    """ Insert given recordings for the given playlist id in the database """
    query = "INSERT INTO playlist.playlist_recording (playlist_id, position, mbid, added_by_id) VALUES %s"
    template = SQL("({playlist_id}, %s, %s, {added_by_id})").format(playlist_id=Literal(playlist_id),
                                                                    added_by_id=Literal(LISTENBRAINZ_USER_ID))
    values = list(enumerate(recordings))
    execute_values(cursor, query, values, template)


def insert_playlists(cursor, playlists):
    """ Create playlists with metadata in the database, the recordings for these are inserted separately. """
    query = """
        INSERT INTO playlist.playlist (creator_id, name, description, public, created_for_id, additional_metadata)
             VALUES %s
          RETURNING created_for_id, id, mbid, created
    """
    template = SQL("""({creator_id}, %s, %s, 't', %s, %s)""").format(creator_id=Literal(LISTENBRAINZ_USER_ID))
    values = [(p["name"], p["description"], p["user_id"], json.dumps(p["additional_metadata"])) for p in playlists]
    results = execute_values(cursor, query, values, template, fetch=True)
    return {r["created_for_id"]: r for r in results}


def exclude_playlists_from_deleted_users(slug, jam_name, all_playlists):
    """ Remove playlists for users who have deleted their accounts. Also, add more metadata to remaining playlists """
    user_ids = [p["user_id"] for p in all_playlists]
    user_details = get_user_details(slug, user_ids)

    # after removing playlists for users who have been deleted but their
    # data has completely not been removed from spark cluster yet
    playlists = []
    playlists_to_export = []
    for playlist in all_playlists:
        user_id = playlist["user_id"]
        if user_id not in user_details:
            continue

        user = user_details[user_id]
        playlist["name"] = f"{jam_name} for {user['username']}, week of {playlist['jam_date']}"
        playlist["existing_url"] = user["existing_url"]
        if not playlist.get("additional_metadata"):
            playlist["additional_metadata"] = {}
        playlist["additional_metadata"]["algorithm_metadata"] = {"source_patch": slug}

        playlists.append(playlist)
        if user["export_to_spotify"]:
            playlists_to_export.append(playlist)

    return playlists, playlists_to_export


def batch_process_playlists(all_playlists, playlists_to_export):
    """ Insert the playlists generated in batch by spark """
    export_to_spotify(playlists_to_export)

    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as curs:
            playlist_ids = insert_playlists(curs, all_playlists)
            for playlist in all_playlists:
                created_for = playlist["user_id"]
                generated_data = playlist_ids[created_for]
                playlist.update(generated_data)
                insert_recordings(curs, playlist["id"], playlist["recordings"])
        conn.commit()
    except Exception:
        current_app.logger.error("Error while batch inserting playlists:", exc_info=True)
    finally:
        conn.close()


def remove_old_playlists(slug, keep):
    """ Once bulk generated playlists have been inserted in Spark, remove all but the
        'keep' number of latest playlists of that slug for all users. """
    query = """
        WITH all_playlists AS (
            SELECT id
                 , rank() OVER (PARTITION BY created_for_id ORDER BY created DESC) AS position
              FROM playlist.playlist
             WHERE creator_id = :creator_id
               AND additional_metadata->'algorithm_metadata'->>'source_patch' = :source_patch
        )   DELETE FROM playlist.playlist pp
                  USING all_playlists ap
                  WHERE pp.id = ap.id
                    AND ap.position > :keep
    """
    with timescale.engine.begin() as connection:
        connection.execute(text(query), {"creator_id": LISTENBRAINZ_USER_ID, "source_patch": slug, "keep": keep})
