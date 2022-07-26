import ujson

from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, request

from listenbrainz.webserver import flash
import listenbrainz.db.user as db_user
import listenbrainz.db.user_setting as db_usersetting
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIInternalServerError,APIBadRequest
from listenbrainz.webserver.views.api_tools import (
    validate_auth_header,
)


user_setting_api_bp = Blueprint('user_setting_api_v1', __name__)


@user_setting_api_bp.route('/timezone', methods=["POST", "OPTIONS"])
@crossdomain
@ratelimit()
def reset_timezone():
  """
  Reset localtimezone for user. A user token (found on  https://listenbrainz.org/profile/)
  must be provided in the Authorization header! 
  
  :reqheader Authorization: Token <user token>
  :statuscode 200: timezone reset.
  :statuscode 400: Bad request. See error message for details.
  :statuscode 401: invalid authorization. See error message for details.
  :resheader Content-Type: *application/json*
  """
  user = validate_auth_header()
  try:
      data = ujson.loads(request.get_data())
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