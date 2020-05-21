import ujson
import listenbrainz.db.user as db_user
import listenbrainz.db.feedback as db_feedback

from datetime import datetime
from flask import Blueprint, current_app, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError, APINotFound,
                                           APIServiceUnavailable,
                                           APIUnauthorized)
from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api import _validate_auth_header
from listenbrainz.webserver.views.api_tools import log_raise_400, DEFAULT_ITEMS_PER_GET, MAX_ITEMS_PER_GET
from listenbrainz.feedback import Feedback
from pydantic import ValidationError

#: Maximum overall feedback size in bytes, to prevent egregious spamming.
MAX_FEEDBACK_SIZE = 10240

feedback_api_bp = Blueprint('feedback_api_v1', __name__)

@feedback_api_bp.route("submit-feedback", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def submit_feedback():
    """
    Submit recording feedback (love/hate) to the server. A user token (found on  https://listenbrainz.org/profile/ )
    must be provided in the Authorization header! Each request should contain only one feedback in the payload.

    Feedback should be submitted for tracks when the user has listened to them and they exist in their listen history.
    If the user hasn't listened to the track or hasn't submitted it to ListenBrainz, it doesn't fully count as a feedback
    and should not be submitted.

    For complete details on the format of the JSON to be POSTed to this endpoint, see :ref:`feedback-json-doc`.

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = _validate_auth_header()

    raw_data = request.get_data()
    try:
        data = ujson.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        log_raise_400("Cannot parse JSON document: %s" % e, raw_data)

    if len(raw_data) > MAX_FEEDBACK_SIZE:
        log_raise_400("JSON document is too large. In aggregate, feedback may not "
                        "be larger than %d characters." % MAX_FEEDBACK_SIZE, data)

    if 'recording_msid' in data and 'score' in data and len(data) > 2:
        log_raise_400("JSON document may only contain recording_msid and "
                      "score top level keys", data)
                    
    try:
        feedback = Feedback(user_id=user["id"], recording_msid=data["recording_msid"], score=data["score"])
    except ValidationError as e:
        log_raise_400("Invalid JSON document submitted: %s" % e, raw_data)
    
    try:
        if feedback.score == 0:
            db_feedback.delete(feedback)
        else:
            db_feedback.insert(feedback)
    except APIServiceUnavailable as e:
        raise
    except Exception as e:
        raise APIInternalServerError("Something went wrong. Please try again.")

    return jsonify({'status': 'ok'})
