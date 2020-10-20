import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording_feedback as db_feedback

from flask import Blueprint, current_app, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIInternalServerError,
                                           APINotFound)

from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api import _validate_auth_header
from listenbrainz.webserver.views.api_tools import (log_raise_400,
                                                    DEFAULT_ITEMS_PER_GET,
                                                    MAX_ITEMS_PER_GET,
                                                    _get_non_negative_param)

from listenbrainz.db.model.recommendation_feedback import (RecommendationFeedbackSubmit,
                                                           RecommendationFeedbackDelete,
                                                           get_allowed_ratings)

from pydantic import ValidationError


recommendation_feedback_api_bp = Blueprint('recommendation_feedback_api_v1', __name__)


@recommendation_feedback_api_bp.route("submit", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def submit_recommendation_feedback():
    """
    Submit recommendation feedback. A user token (found on  https://listenbrainz.org/profile/ )
    must be provided in the Authorization header! Each request should contain only one feedback in the payload.

    A sample feedback may look like::

        {
            "recording_mbid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
            "rating": "love"
        }

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = _validate_auth_header()

    data = request.json

    if 'recording_mbid' not in data or 'rating' not in data:
        log_raise_400("JSON document must contain recording_mbid and rating", data)

    if 'recording_mbid' in data and 'rating' in data and len(data) > 2:
        log_raise_400("JSON document must only contain recording_mbid and rating", data)

    try:
        feedback_submit = RecommendationFeedbackSubmit(user_id=user["id"],
                                                       recording_mbid=data["recording_mbid"],
                                                       rating=data["rating"])
    except ValidationError as e:
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "), data)

    try:
        db_feedback.insert(feedback_submit)
    except Exception as e:
        current_app.logger.error("Error while inserting recommendation feedback: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    return jsonify({'status': 'ok'})


@recommendation_feedback_api_bp.route("delete", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def delete_recommendation_feedback():
    """
    Delete feedback for a user. A user token (found on  https://listenbrainz.org/profile/ )
    must be provided in the Authorization header! Each request should contain only one recording mbid in the payload.
    A sample feedback may look like::

        {
            "recording_mbid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
        }

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback deleted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = _validate_auth_header()

    data = request.json

    if 'recording_mbid' not in data:
        log_raise_400("JSON document must contain recording_mbid", data)

    if 'recording_mbid' in data and len(data) > 1:
        log_raise_400("JSON document must only contain recording_mbid", data)

    try:
        feedback_delete = RecommendationFeedbackDelete(user_id=user["id"], recording_mbid=data["recording_mbid"])
    except ValidationError as e:
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "), data)

    try:
        db_feedback.delete(feedback_delete)
    except Exception as e:
        current_app.logger.error("Error while deleting recommendation feedback: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    return jsonify({'status': 'ok'})


@recommendation_feedback_api_bp.route("/user/<user_name>", methods=["GET"])
@crossdomain()
@ratelimit()
def get_feedback_for_user(user_name):
    """
    Get feedback given by user ``user_name``.

    A sample response may look like:
        {
            count: 1,
            recommendation_feedback: [
                {
                    "created": "1345679998",
                    "recording_mbid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                    "rating": "love"
                },
                "-- more feedback data here ---"
            ],
            offset: 0,
            total_count: 1,
            user_name: 'Vansika'
        }

    If the optional argument ``rating`` is not given, this endpoint will return all the feedback submitted by the user.
    Otherwise filters the feedback to be returned by rating.

    :param rating: Optional, refer to db/model/recommendation_feedback.py for allowed rating values.
    :type rating: ``str``
    :param count: Optional, number of feedback items to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`.
    :type count: ``int``
    :param offset: Optional, number of feedback items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 feedback will be skipped, defaults to 0.
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    rating = request.args.get('rating')

    if rating:
        expected_rating = get_allowed_ratings()
        if rating not in expected_rating:
            log_raise_400("Rating must be in {}".format(expected_rating), request.args)

    offset = _get_non_negative_param('offset', default=0)
    count = _get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    count = min(count, MAX_ITEMS_PER_GET)

    feedback = db_feedback.get_feedback_for_user(user_id=user["id"], limit=count, offset=offset, rating=rating)
    total_count = db_feedback.get_feedback_count_for_user(user["id"])

    feedback = [_format_feedback(fb) for fb in feedback]

    return jsonify({
        "recommendation-feedback": feedback,
        "count": len(feedback),
        "total_count": total_count,
        "offset": offset,
        "user_name": user["musicbrainz_id"]
    })


def _format_feedback(fb):
    """ Format feedback to return via API. Refer to "RecommendationFeedbackSubmit" in db/model/recommendation_feedback.py
        to know the format of recommendation feedback inserted into the db.

        Feedback returned via the API is formatted by:
            -> Converting datetime to timestamp
            -> Removing user id
    """
    fb.created = int(fb.created.timestamp())
    del fb.user_id

    return fb.dict()
