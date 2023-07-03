import json
from datetime import datetime

from flask import current_app
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal
from spotipy import Spotify
from sqlalchemy import text
from troi import Recording, Playlist
from troi.patches.periodic_jams import WEEKLY_JAMS_DESCRIPTION, WEEKLY_EXPLORATION_DESCRIPTION
from troi.tools.spotify_lookup import submit_to_spotify

from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.db.playlist import TROI_BOT_USER_ID
from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.troi.utils import get_existing_playlist_urls


def get_user_details(slug, user_ids):
    """ For all users, get usernames, export preferences and existing spotify playlist urls if preferred to export """
    users_for_urls = []
    details = {}

    query = """
        SELECT "user".id as user_id
             , "user".musicbrainz_id AS musicbrainz_id
             , COALESCE(us.troi->>:export_preference, 'f')::bool AS export_to_spotify
          FROM "user"
     LEFT JOIN user_setting us
            ON us.user_id = "user".id
         WHERE "user".id = ANY(:user_ids)
    """
    with db.engine.connect() as conn:
        results = conn.execute(text(query), {"user_ids": user_ids})
        for r in results:
            details[r.user_id] = {
                "username": r.musicbrainz_id,
                "export_to_spotify": r.export_to_spotify
            }

            if r.export_to_spotify:
                users_for_urls.append(r.user_id)

    existing_urls = get_existing_playlist_urls(user_ids, slug)
    for user_id, detail in details.items():
        detail["existing_url"] = existing_urls.get(user_id)

    return details


def export_to_spotify(slug, playlists):
    """ Export the playlists to spotify.

        If a playlist url for the given user and slug already exists, its updated otherwise a new one is created.
    """
    service = SpotifyService()
    existing_urls = get_existing_playlist_urls([x["user_id"] for x in playlists], slug)

    for playlist in playlists:
        try:
            user_id = playlist["user_id"]
            user = service.get_user(user_id, refresh=True)
            sp = Spotify(auth=user["access_token"])

            recordings = [Recording(mbid=mbid) for mbid in playlist["recordings"]]
            playlist_element = Playlist(recordings=recordings)

            playlist_url, _ = submit_to_spotify(sp, playlist_element, user_id, existing_url=existing_urls.get(user_id))
            playlist["additional_metadata"] = {"external_urls": {"spotify": playlist_url}}
        except Exception:
            current_app.logger.error("Unable to export playlist to spotify:", exc_info=True)


def insert_recordings(cursor, playlist_id: str, recordings: list):
    query = "INSERT INTO playlist.playlist_recording (playlist_id, position, mbid, added_by_id) VALUES %s"
    template = SQL("({playlist_id}, %s, %s, {added_by_id})").format(
        playlist_id=Literal(playlist_id),
        added_by_id=Literal(TROI_BOT_USER_ID)
    )
    values = list(enumerate(recordings))
    execute_values(cursor, query, values, template)


def insert_playlists(cursor, playlists, description: str):
    query = """
        INSERT INTO playlist.playlist (creator_id, name, description, public, created_for_id, additional_metadata)
             VALUES %s
          RETURNING created_for_id, id
    """
    template = SQL("""({creator_id}, %s, {description}, 't', %s, %s)""").format(
        creator_id=Literal(TROI_BOT_USER_ID),
        description=Literal(description)
    )
    values = [(p["name"], p["user_id"], json.dumps(p["additional_metadata"])) for p in playlists]
    results = execute_values(cursor, query, values, template, fetch=True)
    return {r.created_for_id: r.id for r in results}


def filter_and_update_playlists(slug, jam_name, all_playlists):
    """ Remove playlists for users who have deleted their accounts, add more metadata to remaining playlists """
    jam_date = "week of " + datetime.now().strftime("%Y-%m-%d %a")

    user_ids = [p["user_id"] for p in all_playlists]
    user_details = get_user_details(slug, user_ids)

    # after removing playlists for users who have been deleted but their
    # data has completely not been removed from spark cluster yet
    playlists = []
    playlists_to_export = []
    for playlist in playlists:
        user_id = playlist["user_id"]
        if user_id not in user_details:
            continue

        user = user_details[user_id]
        username = user["musicbrainz_id"]
        playlist["name"] = f"{jam_name} for {username}, {jam_date}"
        playlist["additional_metadata"] = {"algorithm_metadata": {"source_patch": slug}}

        playlists.append(playlist)
        if user["export_to_spotify"]:
            playlists_to_export.append(playlist)

    return playlists, playlists_to_export


def batch_process_playlists(slug, all_playlists):
    """ Insert the playlists generated in batch by spark """
    if slug == "weekly-jams":
        jam_name = "Weekly Jams"
        description = WEEKLY_JAMS_DESCRIPTION
    elif slug == "weekly-exploration":
        jam_name = "Weekly Exploration"
        description = WEEKLY_EXPLORATION_DESCRIPTION
    else:
        return

    playlists, playlists_to_export = filter_and_update_playlists(slug, jam_name, all_playlists)

    export_to_spotify(slug, playlists_to_export)

    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor() as cursor:
            playlist_ids = insert_playlists(cursor, playlists, description)
            for playlist in playlists:
                created_for = playlist["user_id"]
                playlist_id = playlist_ids[created_for]
                insert_recordings(cursor, playlist_id, playlist["recordings"])
        conn.commit()
    finally:
        conn.close()


def batch_process_playlists_end(slug):
    """ Once bulk generated playlists have been inserted in Spark, remove all but the
        two latest playlists of that slug for all users. """
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
                    AND ap.position > 2
    """
    with timescale.engine.begin() as connection:
        connection.execute(text(query), {"creator_id": TROI_BOT_USER_ID, "source_patch": slug})
