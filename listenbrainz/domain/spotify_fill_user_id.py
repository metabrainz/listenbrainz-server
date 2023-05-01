from flask import current_app
from psycopg2.extras import execute_values
from spotipy import Spotify
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.domain.spotify import SpotifyService


def get_users_to_update() -> list[dict]:
    """ Retrieve users who have a connected spotify account but we don't have the spotify user id for them. """
    current_app.logger.info("Fetching users to retrieve spotify user ids for")
    query = """
        SELECT user_id
             , musicbrainz_id
             , access_token
             , refresh_token
             , token_expires
          FROM external_service_oauth
          JOIN "user"
            ON "user".id = external_service_oauth.user_id
         WHERE service = 'spotify'
           AND external_user_id IS NULL
    """
    with db.engine.connect() as connection:
        result = connection.execute(text(query))
        rows = result.mappings().all()
    current_app.logger.info(f"Fetched {len(rows)} users to update")
    return rows


def update_users_spotify_ids(users: dict[str, str]):
    """ Update the users in the database by inserting the spotify user ids retrieved earlier. """
    current_app.logger.info("Updating spotify user ids for users")
    query = """
        UPDATE external_service_oauth eso
           SET external_user_id = t.spotify_id
          FROM (VALUES %s) AS t(user_id, spotify_id)
         WHERE eso.user_id = t.user_id
    """
    conn = db.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            execute_values(curs, query, users.items(), template=None)
        conn.commit()
    finally:
        conn.close()
    current_app.logger.info("Completed updating spotify user ids for users")


def retrieve_spotify_user_id(service: SpotifyService, user: dict) -> str:
    """ Check the access token for a given user is still valid and then use it to retrieve the user's spotify id. """
    if service.user_oauth_token_has_expired(user):
        user = service.refresh_access_token(user["user_id"], user["refresh_token"])
    sp = Spotify(auth=user["access_token"])
    spotify_user_id = sp.current_user()["id"]
    return spotify_user_id


def retrieve_spotify_user_ids(users: list[dict]) -> dict[str, str]:
    """ Retrieve spotify user ids for all users. """
    current_app.logger.info("Retrieving spotify user ids")
    service = SpotifyService()
    updates = {}
    for user in users:
        try:
            spotify_id = retrieve_spotify_user_id(service, user)
            updates[user["user_id"]] = spotify_id
            current_app.logger.info(f"Retrieved spotify id successfully for user: {user['musicbrainz_id']}")
        except Exception:
            current_app.logger.error(f"Error while retrieving spotify id for user: {user['musicbrainz_id']}", exc_info=True)
    current_app.logger.info("Finished retrieving spotify user ids")
    return updates


def main():
    """ Script to retrieve spotify user ids of existing users and store those in database. """
    users = get_users_to_update()
    updates = retrieve_spotify_user_ids(users)
    update_users_spotify_ids(updates)
