import listenbrainz.db.user as db_user
import listenbrainz.db.pinned_recording as db_pinned_rec

from flask import Blueprint, current_app, jsonify, request
import math
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIInternalServerError, APINotFound, APINoContent
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api_tools import (
    log_raise_400,
    DEFAULT_ITEMS_PER_GET,
    MAX_ITEMS_PER_GET,
    get_non_negative_param,
    validate_auth_header,
)
from listenbrainz.db.model.pinned_recording import PinnedRecording, WritablePinnedRecording
from pydantic import ValidationError

pinned_recording_api_bp = Blueprint("pinned_rec_api_bp_v1", __name__)


@pinned_recording_api_bp.route("/pin", methods=["POST"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def pin_recording_for_user():
    """
    Pin a recording for user. A user token (found on  https://listenbrainz.org/profile/)
    must be provided in the Authorization header! Each request should contain only one pinned recording item in the payload.

    The format of the JSON to be POSTed to this endpoint should look like the following:

    .. code-block:: json

        {
            "recording_msid": "40ef0ae1-5626-43eb-838f-1b34187519bf",
            "recording_mbid": "40ef0ae1-5626-43eb-838f-1b34187519bf", // Optional
            "blurb_content": "Wow..",
            "pinned_until": 1824001816
        }

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    data = request.json

    if "recording_msid" not in data:
        log_raise_400("JSON document must contain recording_msid: ", data)

    try:
        recording_to_pin = WritablePinnedRecording(
            user_id=user["id"],
            recording_msid=data["recording_msid"],
            recording_mbid=data["recording_mbid"] if "recording_mbid" in data else None,
            blurb_content=data["blurb_content"] if "blurb_content" in data else None,
            pinned_until=data["pinned_until"] if "pinned_until" in data else None,
        )
    except ValidationError as e:
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "), data)

    try:
        db_pinned_rec.pin(recording_to_pin)
    except Exception as e:
        current_app.logger.error("Error while inserting pinned track record: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    return jsonify({"status": "ok"})


@pinned_recording_api_bp.route("/pin/unpin", methods=["POST"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def unpin_recording_for_user():
    """
    Unpins the currently active pinned recording for the user. A user token (found on  https://listenbrainz.org/profile/)
    must be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :statuscode 200: recording unpinned.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 404: could not find the active recording to unpin for the user. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    try:
        recording_unpinned = db_pinned_rec.unpin(user["id"])
    except Exception as e:
        current_app.logger.error("Error while unpinning recording for user: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    if recording_unpinned is False:
        raise APINotFound("Cannot find an active pinned recording for user '%s' to unpin" % (user["musicbrainz_id"]))

    return jsonify({"status": "ok"})


@pinned_recording_api_bp.route("/pin/delete/<pinned_id>", methods=["POST"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def delete_pin_for_user(pinned_id):
    """
    Deletes the pinned recording with given ``pinned_id`` from the server.
    A user token (found on  https://listenbrainz.org/profile/) must be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :param pinned_id: the pinned_id of the pinned recording that should be deleted.
    :type pinned_id: ``int``
    :statuscode 200: recording unpinned.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 404: the requested pinned_id for the user was not found.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    try:
        recording_deleted = db_pinned_rec.delete(pinned_id, user["id"])
    except Exception as e:
        current_app.logger.error("Error while unpinning recording for user: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    if recording_deleted is False:
        raise APINotFound("Cannot find pin with pinned_id '%s' for user '%s'" % (pinned_id, user["musicbrainz_id"]))

    return jsonify({"status": "ok"})


@pinned_recording_api_bp.route("/<user_name>/pins", methods=["GET"])
def get_pins_for_user(user_name):
    """
    Get a list of all recordings ever pinned by a user with given ``user_name`` in descending order of the time
    they were originally pinned. The JSON returned by the API will look like the following:

    .. code-block:: json

        {
            "count": 10,
            "offset": 0,
            "pinned_recordings": [
                {
                    "blurb_content": "Awesome recording!",
                    "created": 1623997168,
                    "pinned_id": 10,
                    "pinned_until": 1623997485,
                    "recording_mbid": null,
                    "recording_msid": "fd7d9162-a284-4a10-906c-faae4f1e166b"
                },
                "-- more pinned recording items here ---"
            ],
            "total_count": 10,
            "user_name": "-- the MusicBrainz ID of the user --"
        }

    :param user_name: the MusicBrainz ID of the user whose pin track history requested.
    :type user_name: ``str``
    :param count: Optional, number of pinned recording items to return,
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of pinned recording items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the most recent 5 pinned recordings from the user will be skipped, defaults to 0
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :statuscode 400: Invalid query parameters. See error message for details.
    :statuscode 404: The requested user was not found.
    :resheader Content-Type: *application/json*
    """
    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    count = min(count, MAX_ITEMS_PER_GET)

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    try:
        pinned_recordings = db_pinned_rec.get_pin_history_for_user(user_id=user["id"], count=count, offset=offset)
    except Exception as e:
        current_app.logger.error("Error while retrieving pins for user: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    pinned_recordings = [_pinned_recording_to_api(pin) for pin in pinned_recordings]
    total_count = db_pinned_rec.get_pin_count_for_user(user_id=user["id"])

    return jsonify(
        {
            "pinned_recordings": pinned_recordings,
            "total_count": total_count,
            "count": len(pinned_recordings),
            "offset": offset,
            "user_name": user_name,
        }
    )


@pinned_recording_api_bp.route("/<user_name>/pins/following", methods=["GET"])
def get_pins_for_user_following(user_name):
    """
    Get a list containing the active pinned recordings for all users in a user's ``user_name``
    following list. The returned pinned recordings are sorted in descending order of the time they were pinned.
    The JSON returned by the API will look like the following:

    .. code-block:: json

        {
            "count": 1,
            "offset": 0,
            "pinned_recordings": [
                {
                "blurb_content": "Spectacular recording!",
                "created": 1624000841,
                "pinned_id": 1,
                "pinned_until": 1624605641,
                "recording_mbid": null,
                "recording_msid": "40ef0ae1-5626-43eb-838f-1b34187519bf",
                "user_name": "-- the MusicBrainz ID of the user who pinned this recording --"
                },
                "-- more pinned recordings from different users here ---"
            ],
            "user_name": "-- the MusicBrainz ID of the original user --"
        }

    :param user_name: the MusicBrainz ID of the user whose followed user's pinned recordings are being requested.
    :type user_name: ``str``
    :param count: Optional, number of pinned recording items to return,
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of pinned recording items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the most recent pinned recordings from the first 5 users will be skipped, defaults to 0
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :statuscode 400: Invalid query parameters. See error message for details.
    :statuscode 404: The requested user was not found.
    :resheader Content-Type: *application/json*
    """

    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)
    offset = get_non_negative_param("offset", default=0)

    count = min(count, MAX_ITEMS_PER_GET)

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    pinned_recordings = db_pinned_rec.get_pins_for_user_following(user_id=user["id"], count=count, offset=offset)
    pinned_recordings = [_pinned_recording_to_api(pin) for pin in pinned_recordings]

    return jsonify(
        {
            "pinned_recordings": pinned_recordings,
            "count": len(pinned_recordings),
            "offset": offset,
            "user_name": user_name,
        }
    )


def _pinned_recording_to_api(pinnedRecording: PinnedRecording) -> dict:
    pin = pinnedRecording.dict()
    pin["created"] = int(pin["created"].timestamp())
    pin["pinned_until"] = int(pin["pinned_until"].timestamp())
    pin["pinned_id"] = pin["row_id"]
    del pin["row_id"]
    del pin["user_id"]
    if pin["user_name"] is None:
        del pin["user_name"]
    return pin
