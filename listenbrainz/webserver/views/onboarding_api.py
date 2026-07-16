"""API endpoints for user onboarding state."""
import orjson
from flask import Blueprint, jsonify, request

import listenbrainz.db.onboarding as db_onboarding
import listenbrainz.db.user as db_user
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APINotFound, APIUnauthorized
from listenbrainz.webserver.views.api_tools import validate_auth_header
from brainzutils.ratelimit import ratelimit

onboarding_api_bp = Blueprint("onboarding_api_v1", __name__)

STATUSES = {"not_started", "in_progress", "skipped", "completed"}
TOURS = {"setup", "listens", "stats", "social"}


@onboarding_api_bp.get("/user/<mb_username:user_name>/onboarding")
@crossdomain
@ratelimit()
def get_onboarding_state(user_name):
    """Return onboarding state for all tours for the given user.

    .. code-block:: json

        {
          "setup": {
            "status": "completed",
            "current_step": 6,
            "unlock_ready": true
          },
          "listens": {
            "status": "in_progress",
            "current_step": 2,
            "unlock_ready": true
          },
          "social": {
            "status": "not_started",
            "current_step": 0,
            "unlock_ready": false
          }
        }

    :statuscode 200: Success
    :statuscode 401: Invalid or missing auth token
    :statuscode 404: User not found
    """
    auth_user = validate_auth_header()
    if auth_user["musicbrainz_id"] != user_name:
        raise APIUnauthorized("You can only view your own onboarding state.")

    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    state = db_onboarding.get_onboarding_state(db_conn, user["id"])
    return jsonify(state)


@onboarding_api_bp.post("/user/<mb_username:user_name>/onboarding")
@crossdomain
@ratelimit()
def update_onboarding_state(user_name):
    """Update progress for a specific onboarding tour.

    .. code-block:: json

        {
          "tour_id": "listens",
          "status": "in_progress",
          "current_step": 3
        }

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: application/json
    :resheader Content-Type: *application/json*
    :statuscode 200: Success
    :statuscode 400: Invalid request body
    :statuscode 401: Invalid or missing auth token
    :statuscode 404: User not found
    """
    auth_user = validate_auth_header()
    if auth_user["musicbrainz_id"] != user_name:
        raise APIUnauthorized("You can only update your own onboarding state.")

    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    try:
        data = orjson.loads(request.get_data())
    except (ValueError, TypeError) as e:
        raise APIBadRequest("Invalid JSON: %s" % str(e))

    tour_id = data.get("tour_id")
    status = data.get("status")
    current_step = data.get("current_step")

    if tour_id not in TOURS:
        raise APIBadRequest("Invalid tour_id. Must be one of: %s" % ", ".join(sorted(TOURS)))
    if status not in STATUSES:
        raise APIBadRequest("Invalid status. Must be one of: %s" % ", ".join(sorted(STATUSES)))
    if not isinstance(current_step, int) or current_step < 0:
        raise APIBadRequest("current_step must be a non-negative integer.")

    db_onboarding.upsert_onboarding_state(
        db_conn,
        user_id=user["id"],
        tour_id=tour_id,
        status=status,
        current_step=current_step,
    )
    return jsonify({"status": "success"})
