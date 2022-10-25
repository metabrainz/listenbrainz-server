""" This module contains code to run the various troi-bot functions after
    recommendations have been generated.
"""
import spotipy
from flask import current_app
from sqlalchemy import text
from troi.core import generate_playlist
from troi.patches.recs_to_playlist import RecommendationsToPlaylistPatch
from troi.patches.daily_jams import DailyJamsPatch

from listenbrainz import db
from listenbrainz.db.playlist import TROI_BOT_USER_ID, TROI_BOT_DEBUG_USER_ID
from listenbrainz.db.user import get_by_mb_id
from listenbrainz.db.user_relationship import get_followers_of_user
from listenbrainz.db.user_timeline_event import create_user_timeline_event, UserTimelineEventType, NotificationMetadata
from listenbrainz.domain.spotify import SpotifyService


def run_post_recommendation_troi_bot():
    """ Top level function called after spark CF recommendations have been completed. """
    # Save playlists for just a handful of people
    users = get_followers_of_user(TROI_BOT_DEBUG_USER_ID)
    users = [user["musicbrainz_id"] for user in users]
    for user in users:
        make_playlist_from_recommendations(user)


def run_daily_jams_troi_bot():
    """ Top level function called hourly to generate daily jams playlists for users """
    # Now generate daily jams (and other in the future) for users who follow troi bot
    users = get_users_for_daily_jams()
    service = SpotifyService()
    for user in users:
        try:
            run_daily_jams(user, service)
            # Add others here
        except Exception as err:
            current_app.logger.error("Cannot create daily-jams for user %s. (%s)" % (user["musicbrainz_id"], str(err)))
            return


def get_users_for_daily_jams():
    """ Retrieve users who follow troi bot and had midnight in their timezone less than 59 minutes ago. """
    query = """
        SELECT "user".musicbrainz_id AS musicbrainz_id
             , "user".id as id
             , to_char(NOW() AT TIME ZONE COALESCE(us.timezone_name, 'GMT'), 'YYYY-MM-DD Dy') AS jam_date
             , COALESCE(us.troi->>'export_to_spotify', 'f')::bool AS export_to_spotify
          FROM user_relationship
          JOIN "user"
            ON "user".id = user_0
     LEFT JOIN user_setting us
            ON us.user_id = user_0  
         WHERE user_1 = :followed
           AND relationship_type = 'follow'
           AND EXTRACT('hour' from NOW() AT TIME ZONE COALESCE(us.timezone_name, 'GMT')) = 0
    """
    with db.engine.connect() as connection:
        result = connection.execute(text(query), {"followed": TROI_BOT_USER_ID})
        return result.mappings().all()


def make_playlist_from_recommendations(user):
    """
        Save the top 100 tracks from the current tracks you might like into a playlist.
    """
    token = current_app.config["WHITELISTED_AUTH_TOKENS"][1]
    args = {
        "user_name": user,
        "upload": True,
        "token": token,
        "created_for": user
    }
    for recs_type in ["top", "similar"]:
        # need to copy dict so that test mocks keep working
        _args = args.copy()
        _args["type"] = recs_type
        generate_playlist(RecommendationsToPlaylistPatch(), _args)


def _get_spotify_details(user_id, service):
    """ Get the spotify token and spotify user id for the given user. If an occurs ignore and proceed. """
    try:
        token = service.get_user(user_id, refresh=True)

        # will be None, if the user has disconnected the spotify account but not disabled the auto-export preference
        if not token:
            return None

        sp = spotipy.Spotify(auth=token["access_token"])
        spotify_user_id = sp.current_user()["id"]
        return {
            "is_public": True,
            "is_collaborative": False,
            "user_id": spotify_user_id,
            "token": token["access_token"]
        }
    except Exception:
        current_app.logger.error("Unable to obtain spotify user details for daily jams:", exc_info=True)
    return None


def run_daily_jams(user, service):
    """  Run the daily-jams patch to create the daily playlist for the given user. """
    token = current_app.config["WHITELISTED_AUTH_TOKENS"][0]
    username = user["musicbrainz_id"]
    args = {
        "user_name": username,
        "upload": True,
        "token": token,
        "created_for": username,
        "jam_date": user["jam_date"]
    }

    if user["export_to_spotify"]:
        spotify = _get_spotify_details(user["id"], service)
        args["spotify"] = spotify

    playlist = generate_playlist(DailyJamsPatch(), args)

    if len(playlist.playlists) > 0:
        url = current_app.config["SERVER_ROOT_URL"] + "/playlist/" + playlist.playlists[0].mbid
        message = f"""Your daily-jams playlist has been updated. <a href="{url}">Give it a listen!</a>."""

        external_urls = getattr(playlist.playlists[0], "external_urls", None)
        if external_urls and len(external_urls) > 0:
            spotify_link = playlist.playlists[0].external_urls
            message += f""" You can also listen it on <a href="{spotify_link}">Spotify!</a>."""

        enter_timeline_notification(username, message)


def enter_timeline_notification(username, message):
    """
       Helper function for createing a timeline notification for troi-bot
    """

    user = get_by_mb_id(username)
    create_user_timeline_event(user["id"],
                               UserTimelineEventType.NOTIFICATION,
                               NotificationMetadata(creator="troi-bot", message=message))
