import ujson

from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, request

import listenbrainz.db.user as db_user
import listenbrainz.db.user_setting as db_usersetting
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIInternalServerError,APIBadRequest


user_setting_api_bp = Blueprint('user_setting_api_v1', __name__)


@user_setting_api_bp.route('/<user_name>/timezone', methods=["POST", "OPTIONS"])
@crossdomain
@ratelimit()
def reset_timezone(user_name):
    try:
        data = ujson.loads(request.get_data())
    except (ValueError, KeyError) as e:
        raise APIBadRequest(f"Invalid JSON: {str(e)}")

    if 'zonename' not in data:
        raise APIBadRequest("JSON document must contain zonename", data)

    zonename = data["zonename"]
    user = db_user.get_by_mb_id(user_name)
    try:
        db_usersetting.set_timezone(user["id"], zonename)
        # flash.info("Your timezone has been saved.")
    except Exception as e:
        raise APIInternalServerError("Something went wrong! Unable to update timezone right now.")
        # flash.error("Something went wrong! Unable to update timezone right now.")
    return jsonify({"status": "ok"})