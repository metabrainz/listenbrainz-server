""" This function contains code to run the various troi-bot functions after
    recommendations have been generated.
"""
from listenbrainz.db.user_relationship import get_following_for_user
from flask import current_app
from troi.core import generate_playlist

TROI_BOT_USER_ID = 12939


def run_post_recommendation_troi_bot(user):
    """
        Top level function called after spark CF recommendations have been completed.
    """

    users = get_following_for_user(TROI_BOT_USER_ID)

    if user in USERS_TO_PROCESS:
        make_playlist_from_recommendations(user["musicbrainz_id"])
        # Add others here


def make_playlist_from_recommendations(user):
    token = current_app.config["WHITELISTED_AUTH_TOKENS"][0]
    for type in ["top", "similar"]:
        generate_playlist("recs-to-playlist", args=[user, type], upload=True, token=token, created_for=user)


def run_daily_jams(user):
    token = current_app.config["WHITELISTED_AUTH_TOKENS"][0]
    generate_playlist("daily-jams", args=[user], upload=True, token=token, created_for=user)
