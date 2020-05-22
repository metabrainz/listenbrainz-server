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
from listenbrainz.webserver.views.api import _validate_auth_header, _parse_int_arg
from listenbrainz.webserver.views.api_tools import log_raise_400, is_valid_uuid
from listenbrainz.feedback import Feedback
from pydantic import ValidationError

feedback_api_bp = Blueprint('feedback_api_v1', __name__)


@feedback_api_bp.route("submit-feedback", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def submit_feedback():
    """
    Submit recording feedback (love/hate) to the server. A user token (found on  https://listenbrainz.org/profile/ )
    must be provided in the Authorization header! Each request should contain only one feedback in the payload.

    For complete details on the format of the JSON to be POSTed to this endpoint, see :ref:`feedback-json-doc`.

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = _validate_auth_header()

    data = request.json
    
    if 'recording_msid' not in data or 'score' not in data:
        log_raise_400("JSON document must contain recording_msid and "
                      "score top level keys", data)

    if 'recording_msid' in data and 'score' in data and len(data) > 2:
        log_raise_400("JSON document may only contain recording_msid and "
                      "score top level keys", data)

    try:
        feedback = Feedback(user_id=user["id"], recording_msid=data["recording_msid"], score=data["score"])
    except ValidationError as e:
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "),
                      data) #  str.replace() to tidy up the error message

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


@feedback_api_bp.route("/user/<user_name>/get-feedback", methods=["GET"])
@crossdomain()
@ratelimit()
def get_feedback_for_user(user_name):
    """
    Get feedback given by user ``user_name``. The format for the JSON returned is defined in our :ref:`feedback-json-doc`.

    If the optional argument ``score`` is not given, this endpoint will return all the feedback submitted by the user.
    Otherwise filters the feedback to be returned by score.

    :param score: If 1 then returns the loved recordings, if -1 returns hated recordings.
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """

    score = _parse_int_arg('score')

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    if score is None:
        feedback = db_feedback.get_feedback_by_user_id(user["id"])
    else:
        if score in [-1, 1]:
            feedback = db_feedback.get_feedback_by_user_id_and_score(user["id"], score)
        else:
            log_raise_400("Score can have a value of 1 or -1.", request.args)

    for i,fb in enumerate(feedback):
        fb.user_id = user_name
        feedback[i] = fb.__dict__

    return jsonify(feedback)


@feedback_api_bp.route("/recording/<recording_msid>/get-feedback", methods=["GET"])
@crossdomain()
@ratelimit()
def get_feedback_for_recording(recording_msid):
    """
    Get feedback for recording with given ``recording_msid``. The format for the JSON returned
    is defined in our :ref:`feedback-json-doc`.

    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """

    if not is_valid_uuid(recording_msid):
            log_raise_400("%s MSID format invalid." % recording_msid)

    feedback = db_feedback.get_feedback_by_recording_msid(recording_msid)

    for i,fb in enumerate(feedback):
        fb.user_id = db_user.get(fb.user_id)["musicbrainz_id"]
        feedback[i] = fb.__dict__

    return jsonify(feedback)
