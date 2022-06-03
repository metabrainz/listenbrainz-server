""" This module contains code to run the various troi-bot functions after
    recommendations have been generated.
"""
from flask import current_app
from troi.core import generate_playlist

from listenbrainz.db.playlist import TROI_BOT_USER_ID
from listenbrainz.db.user import get_by_mb_id
from listenbrainz.db.user_relationship import get_followers_of_user
from listenbrainz.db.user_timeline_event import create_user_timeline_event, UserTimelineEventType, NotificationMetadata


def run_post_recommendation_troi_bot():
    """
        Top level function called after spark CF recommendations have been completed.
    """

    users_to_process = ["mr_monkey", "rob", "akshaaatt", "Damselfish", "lucifer", "alastairp", "CatCat", "atj"]
    if current_app.config['TESTING']:
        current_app.config["WHITELISTED_AUTH_TOKENS"] = ["fake_token"]
        users_to_process = ["lucifer"]

    # Save playlists for just a handful of people
    for user in users_to_process:
        make_playlist_from_recommendations(user)

    # Now generate daily jams (and other in the future) for users who follow troi bot
    users = get_followers_of_user(TROI_BOT_USER_ID)
    users = [user["musicbrainz_id"] for user in users]

    for user in users:
        run_daily_jams(user)
        # Add others here


def make_playlist_from_recommendations(user):
    """
        Save the top 100 tracks from the current tracks you might like into a playlist.
    """
    token = current_app.config["WHITELISTED_AUTH_TOKENS"][0]
    for type in ["top", "similar"]:
        generate_playlist("recs-to-playlist", args=[user, type], upload=True, token=token, created_for=user)


def run_daily_jams(user):
    """
        Run the daily-jams patch to create the daily playlist for the given user.
    """
    token = current_app.config["WHITELISTED_AUTH_TOKENS"][0]
    try:
        url = generate_playlist("daily-jams", args=[user], upload=True, token=token, created_for=user)
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
