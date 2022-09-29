""" This module contains code to run the various troi-bot functions after
    recommendations have been generated.
"""
from flask import current_app
from sqlalchemy import text
from troi.core import generate_playlist

from listenbrainz import db
from listenbrainz.db.playlist import TROI_BOT_USER_ID, TROI_BOT_DEBUG_USER_ID
from listenbrainz.db.user import get_by_mb_id
from listenbrainz.db.user_relationship import get_followers_of_user
from listenbrainz.db.user_timeline_event import create_user_timeline_event, UserTimelineEventType, NotificationMetadata


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
    for user in users:
        run_daily_jams(user["musicbrainz_id"], user["jam_date"])
        # Add others here


def get_users_for_daily_jams():
    """ Retrieve users who follow troi bot and had midnight in their timezone less than 59 minutes ago. """
    query = """
        SELECT "user".musicbrainz_id AS musicbrainz_id
             , "user".id as id
             , to_char(NOW() AT TIME ZONE COALESCE(us.timezone_name, 'GMT'), 'YYYY-MM-DD DY') AS jam_date
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
    for type in ["top", "similar"]:
        generate_playlist("recs-to-playlist", args=[user, type], upload=True, token=token, created_for=user)


def run_daily_jams(user, jam_date):
    """
        Run the daily-jams patch to create the daily playlist for the given user.
    """
    token = current_app.config["WHITELISTED_AUTH_TOKENS"][0]
    try:
        url = generate_playlist("daily-jams", args=[user, jam_date], upload=True, token=token, created_for=user)
    except RuntimeError as err:
        current_app.logger.error("Cannot create daily-jams for user %s. (%s)" % (user, str(err)))
        return
    enter_timeline_notification(user, """Your daily-jams playlist has been updated. <a href="%s">Give it a listen!</a>.""" % url)


def enter_timeline_notification(username, message):
    """
       Helper function for createing a timeline notification for troi-bot
    """

    user = get_by_mb_id(username)
    create_user_timeline_event(user["id"],
                               UserTimelineEventType.NOTIFICATION,
                               NotificationMetadata(creator="troi-bot", message=message))
