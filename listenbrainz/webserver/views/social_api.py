from flask import Blueprint, current_app, jsonify

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
from listenbrainz.webserver import db_conn

from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APINotFound, APIInternalServerError, APIBadRequest
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api_tools import validate_auth_header

social_api_bp = Blueprint('social_api_v1', __name__)


@social_api_bp.get("/user/<user_name>/followers")
@crossdomain
@ratelimit()
def get_followers(user_name: str):
    """
    Fetch the list of followers of the user ``user_name``. Returns a JSON with an array of usernames like these:

    .. code-block:: json

        {
            "followers": ["rob", "mr_monkey", "..."],
            "user": "shivam-kapila"
        }

    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    """
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    try:
        followers = db_user_relationship.get_followers_of_user(db_conn, user["id"])
        followers = [user["musicbrainz_id"] for user in followers]
    except Exception as e:
        current_app.logger.error("Error while trying to fetch followers: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"followers": followers, "user": user["musicbrainz_id"]})


@social_api_bp.get("/user/<user_name>/following")
@crossdomain
@ratelimit()
def get_following(user_name: str):
    """
    Fetch the list of users followed by the user ``user_name``. Returns a JSON with an array of usernames like these:

    .. code-block:: json

        {
            "following": ["rob", "mr_monkey", "..."],
            "user": "shivam-kapila"
        }

    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    """
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    try:
        following = db_user_relationship.get_following_for_user(db_conn, user["id"])
        following = [user["musicbrainz_id"] for user in following]
    except Exception as e:
        current_app.logger.error("Error while trying to fetch following: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"following": following, "user": user["musicbrainz_id"]})


@social_api_bp.post("/user/<user_name>/follow")
@crossdomain
@ratelimit()
def follow_user(user_name: str):
    """
    Follow the user ``user_name``. A user token (found on  https://listenbrainz.org/settings/ ) must
    be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successfully followed the user ``user_name``.
    :statuscode 400:
                    - Already following the user ``user_name``.
                    - Trying to follow yourself.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    current_user = validate_auth_header()
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    if user["musicbrainz_id"] == current_user["musicbrainz_id"]:
        raise APIBadRequest("Whoops, cannot follow yourself.")

    if db_user_relationship.is_following_user(db_conn, current_user["id"], user["id"]):
        raise APIBadRequest("%s is already following user %s" % (current_user["musicbrainz_id"], user["musicbrainz_id"]))

    try:
        db_user_relationship.insert(db_conn, current_user["id"], user["id"], "follow")
    except Exception as e:
        current_app.logger.error("Error while trying to insert a relationship: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"status": "ok"})


@social_api_bp.post("/user/<user_name>/unfollow")
@crossdomain
@ratelimit()
def unfollow_user(user_name: str):
    """
    Unfollow the user ``user_name``. A user token (found on  https://listenbrainz.org/settings/ ) must
    be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successfully unfollowed the user ``user_name``.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    current_user = validate_auth_header()
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    try:
        db_user_relationship.delete(db_conn, current_user["id"], user["id"], "follow")
    except Exception as e:
        current_app.logger.error("Error while trying to delete a relationship: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"status": "ok"})
