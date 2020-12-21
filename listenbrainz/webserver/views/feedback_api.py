import ujson
import listenbrainz.db.user as db_user
import listenbrainz.db.feedback as db_feedback

from flask import Blueprint, current_app, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError, APINotFound,
                                           APIServiceUnavailable,
                                           APIUnauthorized)
from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api import _parse_int_arg
from listenbrainz.webserver.views.api_tools import log_raise_400, is_valid_uuid,\
    DEFAULT_ITEMS_PER_GET, MAX_ITEMS_PER_GET, get_non_negative_param, parse_param_list,\
    validate_auth_header
from listenbrainz.db.model.feedback import Feedback
from pydantic import ValidationError

feedback_api_bp = Blueprint('feedback_api_v1', __name__)


@feedback_api_bp.route("recording-feedback", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def recording_feedback():
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
    user = validate_auth_header()

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
        # Validation errors from the Pydantic model are multi-line. While passing it as a response the new lines
        # are displayed as \n. str.replace() to tidy up the error message so that it becomes a good one line error message.
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "),
                      data)
    try:
        if feedback.score == 0:
            db_feedback.delete(feedback)
        else:
            db_feedback.insert(feedback)
    except Exception as e:
        current_app.logger.error("Error while inserting recording feedback: {}".format(e))
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

    :param score: Optional, If 1 then returns the loved recordings, if -1 returns hated recordings.
    :type score: ``int``
    :param count: Optional, number of feedback items to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`.
    :type count: ``int``
    :param offset: Optional, number of feedback items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 feedback will be skipped, defaults to 0.
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """

    score = _parse_int_arg('score')

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    count = min(count, MAX_ITEMS_PER_GET)

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    if score:
        if score not in [-1, 1]:
            log_raise_400("Score can have a value of 1 or -1.", request.args)

    feedback = db_feedback.get_feedback_for_user(user_id=user["id"], limit=count, offset=offset, score=score)
    total_count = db_feedback.get_feedback_count_for_user(user["id"])

    feedback = [_feedback_to_api(fb) for fb in feedback]

    return jsonify({
        "feedback": feedback,
        "count": len(feedback),
        "total_count": total_count,
        "offset": offset
    })


@feedback_api_bp.route("/recording/<recording_msid>/get-feedback", methods=["GET"])
@crossdomain()
@ratelimit()
def get_feedback_for_recording(recording_msid):
    """
    Get feedback for recording with given ``recording_msid``. The format for the JSON returned
    is defined in our :ref:`feedback-json-doc`.

    :param score: Optional, If 1 then returns the loved recordings, if -1 returns hated recordings.
    :type score: ``int``
    :param count: Optional, number of feedback items to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`.
    :type count: ``int``
    :param offset: Optional, number of feedback items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 feedback will be skipped, defaults to 0.
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """

    if not is_valid_uuid(recording_msid):
        log_raise_400("%s MSID format invalid." % recording_msid)

    score = _parse_int_arg('score')

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    count = min(count, MAX_ITEMS_PER_GET)

    if score:
        if score not in [-1, 1]:
            log_raise_400("Score can have a value of 1 or -1.", request.args)

    feedback = db_feedback.get_feedback_for_recording(recording_msid=recording_msid, limit=count, offset=offset, score=score)
    total_count = db_feedback.get_feedback_count_for_recording(recording_msid)

    feedback = [_feedback_to_api(fb) for fb in feedback]

    return jsonify({
        "feedback": feedback,
        "count": len(feedback),
        "total_count": total_count,
        "offset": offset
    })


@feedback_api_bp.route("/user/<user_name>/get-feedback-for-recordings", methods=["GET"])
@crossdomain()
@ratelimit()
def get_feedback_for_recordings_for_user(user_name):
    """
    Get feedback given by user ``user_name`` for the list of recordings supplied. The format for the JSON returned
    is defined in our :ref:`feedback-json-doc`.

    If the feedback for given recording MSID doesn't exist then a score 0 is returned for that recording.

    :param recordings: comma separated list of recording_msids for which feedback records are to be fetched.
    :type score: ``str``
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """

    recordings = request.args.get('recordings')

    if not recordings:
        log_raise_400("'recordings' has no valid recording MSID.")

    recording_list = parse_param_list(recordings)
    if not len(recording_list):
        raise APIBadRequest("'recordings' has no valid recording MSID.")

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    try:
        feedback = db_feedback.get_feedback_for_multiple_recordings_for_user(user_id=user["id"], recording_list=recording_list)
    except ValidationError as e:
        # Validation errors from the Pydantic model are multi-line. While passing it as a response the new lines
        # are displayed as \n. str.replace() to tidy up the error message so that it becomes a good one line error message.
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "),
                      request.args)

    feedback = [_feedback_to_api(fb) for fb in feedback]

    return jsonify({
        "feedback": feedback,
    })


def _feedback_to_api(fb: Feedback) -> dict:
    fb.user_id = fb.user_name
    del fb.user_name

    return fb.dict()
