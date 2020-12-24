import uuid
import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording_feedback as db_feedback

from flask import Blueprint, current_app, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIInternalServerError,
                                           APINotFound,
                                           APIBadRequest)

from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api_tools import (log_raise_400,
                                                    DEFAULT_ITEMS_PER_GET,
                                                    MAX_ITEMS_PER_GET,
                                                    get_non_negative_param,
                                                    validate_auth_header)

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
    user = validate_auth_header()

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
    user = validate_auth_header()

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
            feedback: [
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
    :statuscode 404: User not found.
    :statuscode 400: Bad request, check ``response['error']`` for more details
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

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    count = min(count, MAX_ITEMS_PER_GET)

    feedback = db_feedback.get_feedback_for_user(user_id=user["id"], limit=count, offset=offset, rating=rating)
    total_count = db_feedback.get_feedback_count_for_user(user["id"])

    feedback = [_format_feedback(fb) for fb in feedback]

    return jsonify({
        "feedback": feedback,
        "count": len(feedback),
        "total_count": total_count,
        "offset": offset,
        "user_name": user["musicbrainz_id"]
    })


@recommendation_feedback_api_bp.route("/user/<user_name>/recordings", methods=["GET"])
@crossdomain()
@ratelimit()
def get_feedback_for_recordings_for_user(user_name):
    """
    Get feedback given by user ``user_name`` for the list of recordings supplied.

    A sample response may look like:
    {
        "feedback": [
            {
                "created": 1604033691,
                "rating": "bad_recommendation",
                "recording_mbid": "9ffabbe4-e078-4906-80a7-3a02b537e251"
            },
            {
                "created": 1604032934,
                "rating": "hate",
                "recording_mbid": "28111d2c-a80d-418f-8b77-6aba58abe3e7"
            }
        ],
        "user_name": "Vansika Pareek"
    }

    An empty response will be returned if the feedback for given recording MBID doesn't exist.

    :param mbids: comma separated list of recording_mbids for which feedback records are to be fetched.
    :type mbids: ``str``
    :statuscode 200: Yay, you have data!
    :statuscode 400: Bad request, check ``response['error']`` for more details.
    :statuscode 404: User not found.
    :resheader Content-Type: *application/json*
    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    mbids = request.args.get('mbids')
    if not mbids:
        raise APIBadRequest("Please provide comma separated recording 'mbids'!")

    recording_list = parse_recording_mbid_list(mbids)

    if not len(recording_list):
        raise APIBadRequest("Please provide comma separated recording mbids!")

    try:
        feedback = db_feedback.get_feedback_for_multiple_recordings_for_user(user_id=user["id"], recording_list=recording_list)
    except ValidationError as e:
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "),
                      request.args)

    recommendation_feedback = [_format_feedback(fb) for fb in feedback]

    return jsonify({
        "feedback": recommendation_feedback,
        "user_name": user_name
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


def parse_recording_mbid_list(mbids):
    """ Check if the passed mbids are valid UUIDs
    """
    mbid_list = []
    for mbid in mbids.split(","):
        try:
            uuid.UUID(mbid)
        except (AttributeError, ValueError):
            raise APIBadRequest("'{}' is not a valid MBID".format(mbid))
        mbid = mbid.strip()
        if not mbid:
            continue
        mbid_list.append(mbid)

    return mbid_list
