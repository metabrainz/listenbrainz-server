""" This function contains code to run the various troi-bot functions after
    recommendations have been generated.
"""
from flask import current_app
from troi.core import generate_playlist

USER_TO_PROCESS = ["mr_monkey", "rob", "akshaaatt", "Damselfish", "lucifer", "alastairp", "CatCat", "atj"]

def run_post_recommendation_troi_bot(user):
    """
        Top level function called after spark CF recommendations have been completed.
    """

    if user in USERS_TO_PROCESS:
        make_playlist_from_recommendations(user)
        # Add others here

def make_playlist_from_recommendations(user):

    token = current.app.config["WHITELISTED_AUTH_TOKENS"][0]
    for type in ["top", "similar"]:
        generate_playlist("recs-to-playlist", args=[user, type], upload=True, token=token, created_for=user)
