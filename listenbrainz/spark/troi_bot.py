""" This function contains code to run the various troi-bot functions after
    recommendations have been generated.
"""
from listenbrainz.db.user_relationship import get_following_for_user
from listenbrainz.db.user_timeline_event import create_user_timeline_event
from data.model.user_timeline_event import (
    UserTimelineEvent,
    UserTimelineEventType,
    UserTimelineEventMetadata,
)
from flask import current_app
from troi.core import generate_playlist

TROI_BOT_USER_ID = 12939
USERS_TO_PROCESS = ["mr_monkey", "rob", "akshaaatt", "Damselfish", "lucifer", "alastairp", "CatCat", "atj"]


def run_post_recommendation_troi_bot():
    """
        Top level function called after spark CF recommendations have been completed.
    """

    # Save playlists for just a handful of people
    for user in USERS_TO_PROCESS:
        make_playlist_from_recommendations(user)

    # Now generate daily jams (and other in the future) for users who follow troi bot
    users = get_following_for_user(TROI_BOT_USER_ID)
    if user in users:
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
        url = generate_playlist("daily-jams", args=[user["musicbrainz_id"]], upload=True, token=token, created_for=user)
    except RuntimeError as err:
        current_app.logger.error("Cannot create daily-jams for user %s. (%s)" % (user["musicbrainz_id"], str(err)))
        return
    enter_timeline_notification(user, """Your daily-jams playlist has been updated. <a href="%s">Give it a listen!</a>.""" % url)


def enter_timeline_notification(user, message):
    """
       Helper function for createing a timeline notification for troi-bot
    """

    create_user_timeline_event(user["id"], 'notification', NotificationMetadata(creator="troi-bot", message=message))
