import orjson
from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, request

import listenbrainz.db.user_setting as db_usersetting
from listenbrainz.troi.troi_bot import SPOTIFY_EXPORT_PREFERENCE
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIInternalServerError, APIBadRequest
from listenbrainz.webserver.views.api_tools import (
    validate_auth_header,
)

user_settings_api_bp = Blueprint('user_settings_api_v1', __name__)


@user_settings_api_bp.route('/timezone', methods=["POST", "OPTIONS"])
@crossdomain
@ratelimit()
def reset_timezone():
    """
    Reset local timezone for user. A user token (found on https://listenbrainz.org/profile/)
    must be provided in the Authorization header! 

    :reqheader Authorization: Token <user token>
    :statuscode 200: timezone reset.
    :statuscode 400: Bad request. See error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()
    try:
        data = orjson.loads(request.get_data())
    except (ValueError, KeyError) as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    if 'zonename' not in data:
        raise APIBadRequest("JSON document must contain zonename", data)

    zonename = data["zonename"]
    try:
        db_usersetting.set_timezone(user["id"], zonename)
    except Exception as e:
        raise APIInternalServerError("Something went wrong! Unable to update timezone right now.")
    return jsonify({"status": "ok"})


@user_settings_api_bp.route('/troi', methods=["POST", "OPTIONS"])
@crossdomain
@ratelimit()
def update_troi_prefs():
    """
    Update troi preferences for the user. A user token (found on https://listenbrainz.org/profile/)
    must be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :statuscode 200: timezone reset.
    :statuscode 400: Bad request. See error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()
    try:
        data = orjson.loads(request.get_data())
    except (ValueError, KeyError) as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    if SPOTIFY_EXPORT_PREFERENCE not in data:
        raise APIBadRequest(f"JSON document must contain {SPOTIFY_EXPORT_PREFERENCE} key", data)

    export_to_spotify = data[SPOTIFY_EXPORT_PREFERENCE]
    if type(export_to_spotify) != bool:
        raise APIBadRequest(f"{SPOTIFY_EXPORT_PREFERENCE} key in the JSON document must be a boolean", data)

    db_usersetting.update_troi_prefs(user["id"], export_to_spotify)
    return jsonify({"status": "ok"})
